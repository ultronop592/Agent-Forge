import time
import contextvars
from contextlib import contextmanager
from typing import Dict, List, Any, Optional, Callable, Iterator
from backend.app.harness.limits import RunLimits
from backend.app.harness.errors import BudgetExceeded, ToolDenied
from backend.app.harness.permissions import build_tool_allowlist

_current_harness: contextvars.ContextVar[Optional["AgentHarness"]] = contextvars.ContextVar(
    "current_harness", default=None
)
_harness_registry: Dict[str, "AgentHarness"] = {}


class AgentHarness:
    def __init__(
        self,
        limits: Optional[RunLimits] = None,
        tool_allowlist: Optional[Dict[str, List[str]]] = None,
        task_id: str = "",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.task_id: str = task_id
        self.limits: RunLimits = limits or RunLimits.from_config()
        self.tool_allowlist: Dict[str, List[str]] = (
            {k.lower(): list(v) for k, v in tool_allowlist.items()}
            if tool_allowlist is not None
            else build_tool_allowlist()
        )
        self.clock: Callable[[], float] = clock
        self.start_time: float = self.clock()
        self.total_paused: float = 0.0
        self._pause_start: Optional[float] = None
        self._pause_reason: str = ""
        self.step_count: int = 0
        self.token_total: int = 0
        self.cost_total: float = 0.0

    def pause(self, reason: str = "") -> None:
        if self._pause_start is None:
            self._pause_start = self.clock()
            self._pause_reason = reason

    def resume(self) -> None:
        if self._pause_start is not None:
            self.total_paused += self.clock() - self._pause_start
            self._pause_start = None
            self._pause_reason = ""

    @contextmanager
    def paused(self, reason: str = "") -> Iterator["AgentHarness"]:
        self.pause(reason)
        try:
            yield self
        finally:
            self.resume()

    def wall_seconds(self) -> float:
        return round(self.clock() - self.start_time, 4)

    def paused_seconds(self) -> float:
        active_pause = (self.clock() - self._pause_start) if self._pause_start is not None else 0.0
        return round(self.total_paused + active_pause, 4)

    def active_seconds(self) -> float:
        return max(0.0, round(self.wall_seconds() - self.paused_seconds(), 4))

    def before_step(self, agent_name: str) -> None:
        if self.step_count >= self.limits.max_steps:
            raise BudgetExceeded("max_steps")
        if self.active_seconds() > self.limits.max_seconds:
            raise BudgetExceeded("max_seconds")
        if (
            self.limits.max_paused_seconds is not None
            and self.paused_seconds() > self.limits.max_paused_seconds
        ):
            raise BudgetExceeded("max_paused_seconds")
        if self.cost_total > self.limits.max_cost_usd:
            raise BudgetExceeded("max_cost_usd")
        if self.token_total > self.limits.max_tokens:
            raise BudgetExceeded("max_tokens")
        self.step_count += 1

    def record(self, tokens: int, cost_usd: float) -> None:
        self.token_total += int(tokens)
        self.cost_total += float(cost_usd)

    def authorize(self, agent_name: str, tool_name: str) -> None:
        allowed = self.tool_allowlist.get(agent_name.lower(), [])
        if tool_name not in allowed:
            raise ToolDenied(agent_name, tool_name)

    def snapshot(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "step_count": self.step_count,
            "max_steps": self.limits.max_steps,
            "token_total": self.token_total,
            "max_tokens": self.limits.max_tokens,
            "cost_total": round(self.cost_total, 6),
            "max_cost_usd": self.limits.max_cost_usd,
            "elapsed_seconds": round(self.active_seconds(), 2),
            "paused_seconds": round(self.paused_seconds(), 2),
            "wall_seconds": round(self.wall_seconds(), 2),
            "max_seconds": self.limits.max_seconds,
        }
        if self.limits.max_paused_seconds is not None:
            data["max_paused_seconds"] = self.limits.max_paused_seconds
        return data


def get_current_harness() -> Optional[AgentHarness]:
    return _current_harness.get()


def set_current_harness(harness: Optional[AgentHarness]) -> None:
    _current_harness.set(harness)


def register_harness(task_id: str, harness: AgentHarness) -> None:
    _harness_registry[task_id] = harness


def unregister_harness(task_id: str) -> None:
    _harness_registry.pop(task_id, None)


def get_harness_for_task(task_id: str) -> Optional[AgentHarness]:
    return _harness_registry.get(task_id)
