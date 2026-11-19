from dataclasses import dataclass
from typing import Optional
from backend.app.core.config import settings


@dataclass
class RunLimits:
    max_steps: int = 25
    max_seconds: float = 300.0
    max_cost_usd: float = 0.50
    max_tokens: int = 120000
    max_paused_seconds: Optional[float] = None

    @classmethod
    def from_config(cls) -> "RunLimits":
        return cls(
            max_steps=getattr(settings, "harness_max_steps", 25),
            max_seconds=getattr(settings, "harness_max_seconds", 300.0),
            max_cost_usd=getattr(settings, "harness_max_cost_usd", 0.50),
            max_tokens=getattr(settings, "harness_max_tokens", 120000),
            max_paused_seconds=getattr(settings, "harness_max_paused_seconds", None),
        )
