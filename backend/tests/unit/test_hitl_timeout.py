import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, patch
import pytest

from backend.app.core.config import settings
from backend.app.database.connection import SessionLocal
from backend.app.database.models import Task, Subtask
from backend.app.workflows.gate_registry import GateRegistry, gate_registry
from backend.app.workflows.orchestrator import planner_node
from backend.app.agents.planner import PlanResponse, SubtaskPlan


def test_hitl_timeout_config() -> None:
    assert hasattr(settings, "hitl_timeout_seconds")
    assert settings.hitl_timeout_seconds == 60.0


def test_gate_registry_open_signal_close() -> None:
    registry = GateRegistry()
    event = registry.open("test-task-gate")
    assert registry.get("test-task-gate") is event
    assert not event.is_set()

    registry.signal("test-task-gate")
    assert event.is_set()

    registry.close("test-task-gate")
    assert registry.get("test-task-gate") is None


@pytest.mark.asyncio
async def test_hitl_plan_approval_timeout_autoproceeds() -> None:
    task_id = "test_hitl_timeout_autoproceed"
    db = SessionLocal()
    try:
        t = Task(id=task_id, prompt="Test plan timeout", plugin_name="default", status="pending")
        db.add(t)
        db.commit()

        mock_plan = PlanResponse(
            reasoning="test",
            subtasks=[SubtaskPlan(title="T1", description="D1", assigned_agent="executor")]
        )

        with patch("backend.app.workflows.orchestrator.planner_agent.create_plan", new=AsyncMock(return_value=mock_plan)):
            with patch.object(settings, "hitl_timeout_seconds", 0.05):
                state: dict[str, Any] = {
                    "task_id": task_id,
                    "prompt": "Test plan timeout",
                    "plugin_name": "default",
                    "subtasks": [],
                    "current_subtask_index": 0,
                    "agent_outputs": {},
                    "verification_results": {},
                    "final_result": "",
                    "retry_count": 0,
                    "verifier_feedback": "",
                    "user_steering": "",
                    "prompt_embedding": [],
                    "agent_sequence": [],
                }
                res = await planner_node(state)
                assert res is not None

        db.expire_all()
        updated = db.query(Task).filter(Task.id == task_id).first()
        assert updated is not None
        assert updated.status == "running"
    finally:
        db.query(Subtask).filter(Subtask.task_id == task_id).delete()
        db.query(Task).filter(Task.id == task_id).delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_hitl_gate_signalling_wakes_immediately() -> None:
    task_id = "test_hitl_signal_wake"
    db = SessionLocal()
    try:
        t = Task(id=task_id, prompt="Test plan signal", plugin_name="default", status="pending")
        db.add(t)
        db.commit()

        mock_plan = PlanResponse(
            reasoning="test",
            subtasks=[SubtaskPlan(title="T1", description="D1", assigned_agent="executor")]
        )

        async def wake_gate_soon() -> None:
            for _ in range(50):
                await asyncio.sleep(0.01)
                if gate_registry.get(task_id) is not None:
                    break
            s_db = SessionLocal()
            try:
                task_rec = s_db.query(Task).filter(Task.id == task_id).first()
                if task_rec:
                    task_rec.status = "running"
                    s_db.commit()
                gate_registry.signal(task_id)
            finally:
                s_db.close()

        t0 = time.monotonic()
        asyncio.create_task(wake_gate_soon())

        with patch("backend.app.workflows.orchestrator.planner_agent.create_plan", new=AsyncMock(return_value=mock_plan)):
            with patch.object(settings, "hitl_timeout_seconds", 30.0):
                state: dict[str, Any] = {
                    "task_id": task_id,
                    "prompt": "Test plan signal",
                    "plugin_name": "default",
                    "subtasks": [],
                    "current_subtask_index": 0,
                    "agent_outputs": {},
                    "verification_results": {},
                    "final_result": "",
                    "retry_count": 0,
                    "verifier_feedback": "",
                    "user_steering": "",
                    "prompt_embedding": [],
                    "agent_sequence": [],
                }
                res = await planner_node(state)
                assert res is not None

        elapsed = time.monotonic() - t0
        assert elapsed < 2.0

        db.expire_all()
        updated = db.query(Task).filter(Task.id == task_id).first()
        assert updated is not None
        assert updated.status == "running"
    finally:
        db.query(Subtask).filter(Subtask.task_id == task_id).delete()
        db.query(Task).filter(Task.id == task_id).delete()
        db.commit()
        db.close()
