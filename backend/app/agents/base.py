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
from backend.app.core.agent_config import agent_config_registry
from backend.app.core.telemetry import calculate_cost, agent_traceable
from backend.app.core.stream import token_stream_manager
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
        self.cost_model = getattr(settings, "cost_model", None) or os.environ.get("COST_MODEL", "gemini-2.5-flash")
        
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
            from backend.app.database.models import Task, Subtask
            # Ensure task exists if foreign key is enforced
            existing_task = db.query(Task).filter(Task.id == task_id).first()
            if not existing_task:
                placeholder_task = Task(id=task_id, prompt=f"Task {task_id}", plugin_name="default", status="running")
                db.add(placeholder_task)
                db.commit()

            valid_subtask_id = None
            if subtask_id:
                sub = db.query(Subtask).filter(Subtask.id == subtask_id).first()
                if sub:
                    valid_subtask_id = subtask_id

            log_entry = AgentLog(
                task_id=task_id,
                subtask_id=valid_subtask_id,
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
            logger.debug(f"Failed to write agent log to database: {e}")
        finally:
            db.close()

    async def _stream_content(self, prompt: str, config: types.GenerateContentConfig, model: Optional[str] = None):
        """
        Stream chunks using generate_content_stream.
        Prefers asynchronous client.aio stream when available, falling back to
        synchronous client.models stream in a dedicated executor thread.
        """
        target_model = model or agent_config_registry.get_model(self.name)
        if hasattr(self.client, "aio") and hasattr(self.client.aio, "models") and hasattr(self.client.aio.models, "generate_content_stream"):
            response_stream = await self.client.aio.models.generate_content_stream(
                model=target_model,
                contents=prompt,
                config=config
            )
            async for chunk in response_stream:
                yield chunk
        else:
            loop = asyncio.get_running_loop()
            def get_sync_stream():
                return self.client.models.generate_content_stream(
                    model=target_model,
                    contents=prompt,
                    config=config
                )
            sync_stream = await loop.run_in_executor(_LLM_EXECUTOR, get_sync_stream)
            for chunk in sync_stream:
                yield chunk

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

        # Read dynamic agent configurations
        agent_cfg = agent_config_registry.get_agent_config(self.name)
        effective_model = agent_cfg.get("model") or self.cost_model or "gemini-2.5-flash"
        effective_temp = float(agent_cfg.get("temperature", 0.2))
        custom_inst = agent_cfg.get("custom_instruction", "")

        full_system_instruction = self.system_instruction
        if custom_inst:
            full_system_instruction = f"{self.system_instruction}\n\n[USER DIRECTIVE FOR {self.name.upper()}]:\n{custom_inst}"

        # Dynamic token budget ceiling
        configured_budget = agent_cfg.get("token_budget")
        effective_max_tokens = max_output_tokens
        if configured_budget and int(configured_budget) > 0:
            effective_max_tokens = int(configured_budget)

        if not self.has_llm:
            # Generate or return mock response
            self.log_db(task_id, subtask_id, "thinking", f"Agent '{self.name}' is running in DEMO mode ({effective_model}).")
            
            if response_schema and mock_response_content:
                try:
                    # Validate mock content matches schema
                    response_schema.model_validate_json(mock_response_content)
                except Exception as e:
                    logger.error(f"Mock content failed validation: {e}")
            
            res_content = mock_response_content or "Demo result from " + self.name

            # Stream words token-by-token for responsive visual feedback
            words = res_content.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                await token_stream_manager.publish_token(
                    task_id=task_id,
                    agent_name=self.name,
                    chunk=chunk,
                    subtask_id=subtask_id
                )
                await asyncio.sleep(0.01)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            
            # Estimate tokens for offline/demo telemetry
            p_tokens = int(len(prompt.split()) * 1.3)
            c_tokens = int(len(res_content.split()) * 1.3)
            tot_tokens = p_tokens + c_tokens
            cost = calculate_cost(p_tokens, c_tokens, model=effective_model)

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
            if effective_max_tokens:
                config_params["max_output_tokens"] = effective_max_tokens
            
            config = types.GenerateContentConfig(
                system_instruction=full_system_instruction,
                temperature=effective_temp,
                **config_params
            )

            max_retries = 3
            
            for attempt in range(max_retries + 1):
                try:
                    collected_chunks: List[str] = []
                    usage_metadata = None

                    async for chunk in self._stream_content(prompt, config, model=effective_model):
                        txt = getattr(chunk, "text", "") or ""
                        if txt:
                            collected_chunks.append(txt)
                            await token_stream_manager.publish_token(
                                task_id=task_id,
                                agent_name=self.name,
                                chunk=txt,
                                subtask_id=subtask_id
                            )
                        if getattr(chunk, "usage_metadata", None):
                            usage_metadata = chunk.usage_metadata

                    result_text = "".join(collected_chunks)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                    # Extract usage metadata & token metrics
                    prompt_tokens = getattr(usage_metadata, "prompt_token_count", None) if usage_metadata else None
                    completion_tokens = getattr(usage_metadata, "candidates_token_count", None) if usage_metadata else None
                    total_tokens = getattr(usage_metadata, "total_token_count", None) if usage_metadata else None

                    if prompt_tokens is None:
                        prompt_tokens = int(len(prompt.split()) * 1.3)
                    if completion_tokens is None:
                        completion_tokens = int(len(result_text.split()) * 1.3)
                    if total_tokens is None:
                        total_tokens = prompt_tokens + completion_tokens

                    cost_usd = calculate_cost(prompt_tokens, completion_tokens, model=effective_model)

                    # Log the final agent output with token & latency telemetry
                    self.log_db(
                        task_id, subtask_id, "output", result_text,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        latency_ms=elapsed_ms,
                        cost_usd=cost_usd
                    )

                    # Surface high-signal telemetry log for Thinking Console display
                    self.log_db(
                        task_id, subtask_id, "telemetry",
                        f"📊 [{self.name} Metrics] Latency: {elapsed_ms:.1f}ms | "
                        f"Tokens: {total_tokens:,} (Prompt: {prompt_tokens:,}, Output: {completion_tokens:,}) | "
                        f"Est. Cost: ${cost_usd:.6f}"
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

