import time
import pytest
from typing import List, Dict, Any
from backend.app.harness.limits import RunLimits
from backend.app.harness.errors import BudgetExceeded, ToolDenied
from backend.app.harness.harness import AgentHarness
from backend.app.harness.permissions import build_tool_allowlist
from backend.app.plugins.base_plugin import BaseWorkflowPlugin


class SamplePlugin(BaseWorkflowPlugin):
    @property
    def name(self) -> str:
        return "Sample"

    @property
    def plugin_id(self) -> str:
        return "sample"

    @property
    def description(self) -> str:
        return "Sample plugin for test"

    def get_custom_system_instruction(self, agent_name: str) -> str:
        return ""

    def get_default_subtasks(self, prompt: str) -> List[Dict[str, Any]]:
        return []

    def get_tool_permissions(self, agent_name: str) -> List[str]:
        if agent_name.lower() == "executor":
            return ["mcp_custom_tool"]
        return []


def test_harness_trips_max_steps() -> None:
    limits = RunLimits(max_steps=2)
    harness = AgentHarness(limits=limits)
    harness.before_step("planner")
    harness.before_step("analyst")
    with pytest.raises(BudgetExceeded) as exc_info:
        harness.before_step("executor")
    assert exc_info.value.reason_code == "max_steps"


def test_harness_trips_max_seconds() -> None:
    limits = RunLimits(max_seconds=0.01)
    harness = AgentHarness(limits=limits)
    time.sleep(0.02)
    with pytest.raises(BudgetExceeded) as exc_info:
        harness.before_step("planner")
    assert exc_info.value.reason_code == "max_seconds"


def test_harness_trips_max_cost_usd() -> None:
    limits = RunLimits(max_cost_usd=0.25)
    harness = AgentHarness(limits=limits)
    harness.record(tokens=100, cost_usd=0.26)
    with pytest.raises(BudgetExceeded) as exc_info:
        harness.before_step("planner")
    assert exc_info.value.reason_code == "max_cost_usd"


def test_harness_trips_max_tokens() -> None:
    limits = RunLimits(max_tokens=500)
    harness = AgentHarness(limits=limits)
    harness.record(tokens=501, cost_usd=0.01)
    with pytest.raises(BudgetExceeded) as exc_info:
        harness.before_step("planner")
    assert exc_info.value.reason_code == "max_tokens"


def test_harness_authorize_allows_and_denies() -> None:
    harness = AgentHarness()
    harness.authorize("analyst", "tavily_search")
    harness.authorize("memory_agent", "memory_search")

    with pytest.raises(ToolDenied) as exc_planner:
        harness.authorize("planner", "tavily_search")
    assert exc_planner.value.agent_name == "planner"
    assert exc_planner.value.tool_name == "tavily_search"

    with pytest.raises(ToolDenied) as exc_executor:
        harness.authorize("executor", "custom_mcp_tool")
    assert exc_executor.value.agent_name == "executor"

    with pytest.raises(ToolDenied) as exc_verifier:
        harness.authorize("verifier", "tavily_search")
    assert exc_verifier.value.agent_name == "verifier"

    plugin = SamplePlugin()
    plugin_allowlist = build_tool_allowlist(plugin)
    plugin_harness = AgentHarness(tool_allowlist=plugin_allowlist)
    plugin_harness.authorize("executor", "mcp_custom_tool")


def test_harness_record_and_snapshot() -> None:
    limits = RunLimits(max_steps=10, max_seconds=100.0, max_cost_usd=1.0, max_tokens=10000)
    harness = AgentHarness(limits=limits, task_id="task-123")
    harness.before_step("planner")
    harness.record(tokens=250, cost_usd=0.005)
    snap = harness.snapshot()
    assert snap["step_count"] == 1
    assert snap["max_steps"] == 10
    assert snap["token_total"] == 250
    assert snap["cost_total"] == 0.005
    assert snap["max_cost_usd"] == 1.0
    assert snap["max_tokens"] == 10000
    assert snap["elapsed_seconds"] >= 0.0
    assert snap["max_seconds"] == 100.0
