import os
import json
import logging
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Type, Any, Dict, List
from pydantic import BaseModel
from google import genai
from google.genai import types
from backend.app.core.config import settings
from backend.app.core.telemetry import calculate_cost, agent_traceable
from backend.app.database.connection import SessionLocal
from backend.app.database.models import AgentLog

logger = logging.getLogger("agentforge.agents")
logger.setLevel(logging.INFO)

# Dedicated thread pool for LLM API calls, decoupled from FastAPI's default pool.
# This prevents DB writes and other blocking I/O from queuing up behind LLM calls.
_LLM_EXECUTOR = ThreadPoolExecutor(max_workers=10, thread_name_prefix="agentforge-llm")


class BaseAgent:
    def __init__(self, name: str, system_instruction: str):
        self.name = name
        self.system_instruction = system_instruction
        self.api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.has_llm = True
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI Client: {e}")
                self.has_llm = False
        else:
            logger.warning(f"No GEMINI_API_KEY found. '{self.name}' will operate in demo/mock mode.")
            self.has_llm = False

    def log_db(
        self,
        task_id: str,
        subtask_id: Optional[str],
        log_type: str,
        content: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: float = 0.0,
        cost_usd: float = 0.0,
    ):
        db = SessionLocal()
        try:
            log_entry = AgentLog(
                task_id=task_id,
                subtask_id=subtask_id,
                agent_name=self.name,
                log_type=log_type,
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to write agent log to database: {e}")
        finally:
            db.close()

    @agent_traceable(name="Agent_LLM_Execution", run_type="llm")
    async def execute_llm(
        self,
        prompt: str,
        task_id: str,
        subtask_id: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
        mock_response_content: Optional[str] = None,
        max_output_tokens: Optional[int] = None
    ) -> str:
        # Log that thinking is starting
        self.log_db(task_id, subtask_id, "thinking", f"Agent '{self.name}' is analyzing prompt:\n\"{prompt[:150]}...\"")
        start_time = time.perf_counter()

        if not self.has_llm:
            # Generate or return mock response
            self.log_db(task_id, subtask_id, "thinking", f"Agent '{self.name}' is running in DEMO mode.")
            await asyncio.sleep(0.3)  # Simulate network time
            
            if response_schema and mock_response_content:
                try:
                    # Validate mock content matches schema
                    response_schema.model_validate_json(mock_response_content)
                except Exception as e:
                    logger.error(f"Mock content failed validation: {e}")
            
            res_content = mock_response_content or "Demo result from " + self.name
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            
            # Estimate tokens for offline/demo telemetry
            p_tokens = int(len(prompt.split()) * 1.3)
            c_tokens = int(len(res_content.split()) * 1.3)
            tot_tokens = p_tokens + c_tokens
            cost = calculate_cost(p_tokens, c_tokens, model="gemini-2.5-flash")

            self.log_db(
                task_id, subtask_id, "output", res_content,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=tot_tokens,
                latency_ms=elapsed_ms,
                cost_usd=cost
            )
            return res_content

        try:
            config_params = {}
            if response_schema:
                config_params["response_mime_type"] = "application/json"
                config_params["response_schema"] = response_schema
            if max_output_tokens:
                config_params["max_output_tokens"] = max_output_tokens
            
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.2,
                **config_params
            )

            loop = asyncio.get_running_loop()
            max_retries = 3
            
            for attempt in range(max_retries + 1):
                try:
                    def call_api():
                        return self.client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt,
                            config=config
                        )
                        
                    response = await loop.run_in_executor(_LLM_EXECUTOR, call_api)
                    result_text = response.text or ""
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                    # Extract usage metadata & token metrics
                    usage = getattr(response, "usage_metadata", None)
                    prompt_tokens = getattr(usage, "prompt_token_count", None)
                    completion_tokens = getattr(usage, "candidates_token_count", None)
                    total_tokens = getattr(usage, "total_token_count", None)

                    if prompt_tokens is None:
                        prompt_tokens = int(len(prompt.split()) * 1.3)
                    if completion_tokens is None:
                        completion_tokens = int(len(result_text.split()) * 1.3)
                    if total_tokens is None:
                        total_tokens = prompt_tokens + completion_tokens

                    cost_usd = calculate_cost(prompt_tokens, completion_tokens, model="gemini-2.5-flash")

                    # Log the final agent output with token & latency telemetry
                    self.log_db(
                        task_id, subtask_id, "output", result_text,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        latency_ms=elapsed_ms,
                        cost_usd=cost_usd
                    )

                    # Surface high-signal telemetry log
                    self.log_db(
                        task_id, subtask_id, "telemetry",
                        f"📊 [{self.name} Metrics] Latency: {elapsed_ms:.1f}ms | "
                        f"Tokens: {total_tokens:,} (Prompt: {prompt_tokens:,}, Output: {completion_tokens:,}) | "
                        f"Est. Cost: ${cost_usd:.6f}",
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        latency_ms=elapsed_ms,
                        cost_usd=cost_usd
                    )
                    return result_text
                
                except Exception as e:
                    err_str = str(e)
                    is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                    if is_rate_limit and attempt < max_retries:
                        # Parse the suggested retry delay from the API error, default 60s
                        import re as _re
                        match = _re.search(r"retryDelay.*?(\d+)s", err_str)
                        sleep_time = int(match.group(1)) + 3 if match else 62
                        retry_msg = (
                            f"⚠️ Gemini rate limit hit (429). Waiting {sleep_time}s before retry "
                            f"{attempt + 1}/{max_retries}..."
                        )
                        self.log_db(task_id, subtask_id, "thinking", retry_msg)
                        logger.warning(retry_msg)
                        await asyncio.sleep(sleep_time)
                        continue
                    raise e

        except Exception as e:
            logger.error(f"API call failed for agent '{self.name}': {e}")
            self.log_db(task_id, subtask_id, "error", f"API Call failed: {str(e)}")
            # Fallback to mock response rather than hard crashing
            if mock_response_content:
                self.log_db(task_id, subtask_id, "thinking", "Falling back to demo content due to API failure.")
                return mock_response_content
            raise e
