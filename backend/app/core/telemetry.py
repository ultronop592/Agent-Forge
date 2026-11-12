import os
import json
import time
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from pydantic import BaseModel

from backend.app.core.config import settings

logger = logging.getLogger("agentforge.telemetry")


class ModelPrice(BaseModel):
    input_per_million: float
    output_per_million: float


def load_model_prices(config_path: Optional[str] = None) -> Dict[str, ModelPrice]:
    path = config_path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config",
        "model_prices.json"
    )
    with open(path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    return {model: ModelPrice(**price_data) for model, price_data in raw_data.items()}


def calculate_cost(prompt_tokens: int, completion_tokens: int, model: Optional[str] = None) -> float:
    if not model:
        model = getattr(settings, "cost_model", None) or os.environ.get("COST_MODEL", "gemini-2.5-flash")
    prices = load_model_prices()
    if model not in prices:
        raise ValueError(f"Unknown model: '{model}'. Pricing configuration not found in model_prices.json.")
    pricing = prices[model]
    input_cost = (prompt_tokens / 1_000_000.0) * pricing.input_per_million
    output_cost = (completion_tokens / 1_000_000.0) * pricing.output_per_million
    return round(input_cost + output_cost, 7)


def is_langsmith_enabled() -> bool:
    has_key = bool(os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY") or settings.langsmith_api_key)
    tracing_flag = (
        os.environ.get("LANGSMITH_TRACING", "").lower() in ("true", "1") or
        os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1") or
        settings.langsmith_tracing
    )
    return has_key and tracing_flag


def setup_langsmith() -> None:
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

        logger.info(f"🛰️ LangSmith Tracing ENABLED for project: '{project}' (Endpoint: {endpoint})")
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        os.environ["LANGSMITH_TRACING"] = "false"
        logger.info("📊 LangSmith Tracing is operating in LOCAL TELEMETRY mode (token, latency & cost tracking enabled in DB).")


def agent_traceable(
    name: Optional[str] = None,
    run_type: str = "chain",
    tags: Optional[list] = None,
    metadata: Optional[dict] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
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
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)
            return wrapper
    return decorator
