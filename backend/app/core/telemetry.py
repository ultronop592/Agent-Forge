import os
import time
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps

from backend.app.core.config import settings

logger = logging.getLogger("agentforge.telemetry")

# Token pricing per 1,000,000 tokens (USD)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gemini-2.5-flash": {
        "input_per_million": 0.075,
        "output_per_million": 0.30,
    },
    "gemini-1.5-flash": {
        "input_per_million": 0.075,
        "output_per_million": 0.30,
    },
    "gemini-1.5-pro": {
        "input_per_million": 1.25,
        "output_per_million": 5.00,
    },
    "models/gemini-embedding-001": {
        "input_per_million": 0.025,
        "output_per_million": 0.0,
    },
    "default": {
        "input_per_million": 0.10,
        "output_per_million": 0.40,
    }
}


def calculate_cost(prompt_tokens: int, completion_tokens: int, model: str = "gemini-2.5-flash") -> float:
    """Calculate the estimated USD cost of an LLM call based on token usage."""
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
    input_cost = (prompt_tokens / 1_000_000.0) * pricing["input_per_million"]
    output_cost = (completion_tokens / 1_000_000.0) * pricing["output_per_million"]
    return round(input_cost + output_cost, 7)


def is_langsmith_enabled() -> bool:
    """Check if LangSmith tracing is actively configured."""
    has_key = bool(os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY") or settings.langsmith_api_key)
    tracing_flag = (
        os.environ.get("LANGSMITH_TRACING", "").lower() in ("true", "1") or
        os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1") or
        settings.langsmith_tracing
    )
    return has_key and tracing_flag


def setup_langsmith():
    """Configure environment variables for LangSmith and LangGraph tracing."""
    api_key = os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY") or settings.langsmith_api_key
    project = os.environ.get("LANGSMITH_PROJECT") or os.environ.get("LANGCHAIN_PROJECT") or settings.langsmith_project or "AgentForge"
    endpoint = os.environ.get("LANGSMITH_ENDPOINT") or os.environ.get("LANGCHAIN_ENDPOINT") or settings.langsmith_endpoint or "https://api.smith.langchain.com"
    tracing_enabled = (
        os.environ.get("LANGSMITH_TRACING", "").lower() in ("true", "1") or
        os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1") or
        settings.langsmith_tracing
    )

    if tracing_enabled and api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = project
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint
        
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = api_key
        os.environ["LANGSMITH_PROJECT"] = project
        os.environ["LANGSMITH_ENDPOINT"] = endpoint
        os.environ["LANGSMITH_PROJECT"] = project
        os.environ["LANGSMITH_ENDPOINT"] = endpoint

        logger.info(f"🛰️ LangSmith Tracing ENABLED for project: '{project}' (Endpoint: {endpoint})")
    else:
        # Graceful fallback: local telemetry without LangSmith remote export
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        os.environ["LANGSMITH_TRACING"] = "false"
        logger.info("📊 LangSmith Tracing is operating in LOCAL TELEMETRY mode (token, latency & cost tracking enabled in DB).")


def agent_traceable(
    name: Optional[str] = None,
    run_type: str = "chain",
    tags: Optional[list] = None,
    metadata: Optional[dict] = None
):
    """
    Decorator that applies LangSmith @traceable if available and enabled,
    while gracefully executing without dependencies if disabled.
    """
    def decorator(func: Callable):
        try:
            from langsmith import traceable
            trace_func = traceable(
                name=name or func.__name__,
                run_type=run_type,
                tags=tags or ["agentforge"],
                metadata=metadata or {}
            )
            return trace_func(func)
        except Exception as e:
            logger.debug(f"LangSmith traceable wrapper skipped: {e}")
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
    return decorator
