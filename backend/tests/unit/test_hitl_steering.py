import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from backend.app.database.connection import SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog
from backend.app.workflows.state import AgentState
from backend.app.agents.executor import ExecutorAgent
from backend.app.agents.verifier import VerificationResponse
from backend.app.workflows.orchestrator import (
    executor_node,
    verifier_node,
    update_subtask_in_db,
)


@pytest.mark.asyncio
async def test_executor_run_subtask_prioritizes_user_steering_prompt():
    """Verify that human steering is elevated with top-priority directive above verifier critique."""
    executor = ExecutorAgent()
    captured_prompt = None

    async def mock_execute_llm(prompt, task_id, subtask_id, mock_response_content, max_output_tokens):
        nonlocal captured_prompt
        captured_prompt = prompt
        return mock_response_content

    with patch.object(executor, "execute_llm", side_effect=mock_execute_llm):
        steering_text = "Ensure all endpoints return JSON:API standard envelopes."
        verifier_text = "Missing error handler for 404 status."

        await executor.run_subtask(
            subtask_title="Implement User API",
            subtask_desc="Build REST API for user resources",
            context="Prior context data",
            task_id="test_t1",
            subtask_id="test_s1",
            verifier_feedback=verifier_text,
            user_steering=steering_text,
        )

        assert captured_prompt is not None
        assert "👑 MANDATORY HUMAN OPERATOR DIRECTIVE (TOP PRIORITY):" in captured_prompt
        assert steering_text in captured_prompt
        assert verifier_text in captured_prompt
        # Verify steering directive appears before verifier feedback in prompt
        steering_pos = captured_prompt.index("MANDATORY HUMAN OPERATOR DIRECTIVE")
        verifier_pos = captured_prompt.index("A previous output was rejected by the Verifier")
        assert steering_pos < verifier_pos


@pytest.mark.asyncio
async def test_executor_run_subtask_demo_mode_includes_steering():
    """Verify that demo/mock execution mode incorporates the user's steering directive dynamically."""
    executor = ExecutorAgent()
    executor.has_llm = False  # Explicitly force demo/mock mode
    steering_text = "Add strict exponential backoff retry logic."

    output = await executor.run_subtask(
        subtask_title="Network Client",
        subtask_desc="Build resilient HTTP client",
        context="context",
        task_id="test_t2",
        subtask_id="test_s2",
        user_steering=steering_text,
    )

    assert "## 🎯 Human Steering Directive Applied" in output
    assert steering_text in output
    assert "Re-aligned execution output with human supervisory requirements." in output


def test_update_subtask_in_db_persists_description():
    """Verify update_subtask_in_db persists description changes to DB."""
    db = SessionLocal()
    task = Task(id="test_db_task_1", prompt="Test Prompt", plugin_name="default", status="running")
    subtask = Subtask(
        id="test_db_sub_1",
        task_id="test_db_task_1",
        title="Sub 1",
        description="Original description",
        assigned_agent="executor",
        status="pending",
        order_index=0,
    )
    db.add(task)
    db.add(subtask)
    db.commit()
    db.close()

    try:
        new_desc = "Original description\n\n[Human Steering Override]: Use PostgreSQL 16"
        update_subtask_in_db("test_db_sub_1", "running", description=new_desc)

        db2 = SessionLocal()
        updated_sub = db2.query(Subtask).filter(Subtask.id == "test_db_sub_1").first()
        assert updated_sub is not None
        assert updated_sub.description == new_desc
        assert updated_sub.status == "running"
        db2.close()
    finally:
        db_clean = SessionLocal()
        db_clean.query(Subtask).filter(Subtask.task_id == "test_db_task_1").delete()
        db_clean.query(Task).filter(Task.id == "test_db_task_1").delete()
        db_clean.commit()
        db_clean.close()


@pytest.mark.asyncio
async def test_verifier_node_captures_steering_and_updates_subtask_and_state():
    """Verify verifier_node extracts steering, updates DB subtask description, and returns user_steering."""
    task_id = "test_hitl_task_99"
    sub_id = "test_hitl_sub_99"

    db = SessionLocal()
    task = Task(id=task_id, prompt="Build backend", plugin_name="default", status="running")
    subtask = Subtask(
        id=sub_id,
        task_id=task_id,
        title="Executor Deliverable",
        description="Implement core API",
        assigned_agent="executor",
        status="completed",
        order_index=0,
    )
    # Add steering log as if user steered via /tasks/{task_id}/steer
    steering_log = AgentLog(
        task_id=task_id,
        agent_name="User",
        log_type="steering",
        content="Refactor to use Pydantic v2 BaseModels with alias generator.",
    )
    db.add(task)
    db.add(subtask)
    db.add(steering_log)
    db.commit()
    db.close()

    try:
        state: AgentState = {
            "task_id": task_id,
            "prompt": "Build backend",
            "plugin_name": "default",
            "subtasks": [
                {
                    "id": sub_id,
                    "title": "Executor Deliverable",
                    "description": "Implement core API",
                    "assigned_agent": "executor",
                }
            ],
            "current_subtask_index": 1,
            "agent_outputs": {sub_id: "Initial API implementation"},
            "verification_results": {},
            "final_result": "",
            "retry_count": 0,
            "verifier_feedback": "",
            "user_steering": "",
            "prompt_embedding": [],
            "agent_sequence": [],
            "manager_quality_scores": {},
            "manager_skip_flags": {},
            "agent_retry_counts": {},
        }

        mock_v_res = VerificationResponse(
            is_valid=False,
            confidence_score=0.45,
            feedback="Models lack strict input validation schema.",
            verified_output="",
        )

        async def simulate_user_steering():
            await asyncio.sleep(0.1)
            s_db = SessionLocal()
            t = s_db.query(Task).filter(Task.id == task_id).first()
            if t:
                t.status = "running"
                s_db.commit()
            s_db.close()

        asyncio.create_task(simulate_user_steering())

        with patch("backend.app.workflows.orchestrator.verifier_agent.verify_output", new=AsyncMock(return_value=mock_v_res)):
            result_state = await verifier_node(state)

            # Assert steering is extracted into state
            assert result_state["user_steering"] == "Refactor to use Pydantic v2 BaseModels with alias generator."
            assert result_state["verifier_feedback"] == "Models lack strict input validation schema."
            assert result_state["retry_count"] == 1
            assert result_state["verification_results"]["is_valid"] is False

            # Assert in-memory subtask description was updated
            updated_subtask = result_state["subtasks"][0]
            assert "[Human Steering Override]: Refactor to use Pydantic v2 BaseModels with alias generator." in updated_subtask["description"]

            # Assert DB subtask description was updated
            db2 = SessionLocal()
            db_sub = db2.query(Subtask).filter(Subtask.id == sub_id).first()
            assert db_sub is not None
            assert "[Human Steering Override]: Refactor to use Pydantic v2 BaseModels with alias generator." in db_sub.description
            db2.close()
    finally:
        db_clean = SessionLocal()
        db_clean.query(AgentLog).filter(AgentLog.task_id == task_id).delete()
        db_clean.query(Subtask).filter(Subtask.task_id == task_id).delete()
        db_clean.query(Task).filter(Task.id == task_id).delete()
        db_clean.commit()
        db_clean.close()


@pytest.mark.asyncio
async def test_executor_node_passes_steering_to_executor_agent():
    """Verify executor_node extracts user_steering from state and passes it to executor_agent.run_subtask."""
    task_id = "test_exec_node_task"
    sub_id = "test_exec_node_sub"

    state: AgentState = {
        "task_id": task_id,
        "prompt": "Create parser",
        "plugin_name": "default",
        "subtasks": [
            {
                "id": sub_id,
                "title": "Parse Data",
                "description": "Parse incoming log lines",
                "assigned_agent": "executor",
            }
        ],
        "current_subtask_index": 0,
        "agent_outputs": {},
        "verification_results": {},
        "final_result": "",
        "retry_count": 1,
        "verifier_feedback": "Handle corrupted UTF-8 byte sequences.",
        "user_steering": "Use errors='replace' and add defensive regex.",
        "prompt_embedding": [],
        "agent_sequence": [],
        "manager_quality_scores": {},
        "manager_skip_flags": {},
        "agent_retry_counts": {},
    }

    with patch("backend.app.workflows.orchestrator.executor_agent.run_subtask", new=AsyncMock(return_value="Mocked parser")) as mock_run:
        with patch("backend.app.workflows.orchestrator.update_subtask_in_db"):
            result = await executor_node(state)

            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args.kwargs
            assert call_kwargs["user_steering"] == "Use errors='replace' and add defensive regex."
            assert call_kwargs["verifier_feedback"] == "Handle corrupted UTF-8 byte sequences."
            assert result["agent_outputs"][sub_id] == "Mocked parser"
