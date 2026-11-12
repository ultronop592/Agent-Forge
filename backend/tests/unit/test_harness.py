import time
import asyncio
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


@pytest.mark.asyncio
async def test_reject_cancels_running_asyncio_task(db_session: Any) -> None:
    from backend.app.database.models import Task
    from backend.app.workflows.task_registry import task_registry
    from backend.app.api.tasks import reject_task, RejectPayload

    task_id = "test-task-cancel-id"
    db_task = Task(id=task_id, prompt="Test cancel", plugin_name="default", status="running")
    db_session.add(db_task)
    db_session.commit()

    async def long_running_coro() -> None:
        await asyncio.sleep(100.0)

    bg_task = asyncio.create_task(long_running_coro())
    task_registry.register(task_id, bg_task)

    try:
        res = reject_task(task_id=task_id, payload=RejectPayload(reason="User abort"), db=db_session)
        assert res["status"] == "cancelled"
        assert bg_task.cancelled() or bg_task.cancelling() > 0
        with pytest.raises(asyncio.CancelledError):
            await bg_task
    finally:
        task_registry.unregister(task_id)


@pytest.mark.asyncio
async def test_mcp_client_tool_authorization() -> None:
    from backend.app.harness.harness import set_current_harness
    from backend.app.mcp.client import mcp_manager

    harness = AgentHarness()
    set_current_harness(harness)
    try:
        with pytest.raises(ToolDenied) as exc:
            await mcp_manager.call_tool("test_server", "unauthorized_tool", {}, agent_name="executor")
        assert exc.value.agent_name == "executor"
        assert exc.value.tool_name == "unauthorized_tool"
    finally:
        set_current_harness(None)


def test_task_model_failure_reason_field() -> None:
    from backend.app.database.models import Task

    t = Task(prompt="Fail test", plugin_name="default", status="failed", failure_reason='{"reason_code": "max_cost_usd"}')
    d = t.to_dict()
    assert d["failure_reason"] == '{"reason_code": "max_cost_usd"}'


