import os
import pytest
from unittest.mock import patch, MagicMock

from backend.app.core.telemetry import (
    calculate_cost,
    setup_langsmith,
    is_langsmith_enabled,
    agent_traceable,
    MODEL_PRICING
)
from backend.app.agents.base import BaseAgent
from backend.app.agents.manager_agent import ManagerAgent
from backend.app.database.connection import SessionLocal
from backend.app.database.models import Task, AgentLog


def test_calculate_cost_gemini():
    # 1,000,000 prompt tokens @ $0.075 + 1,000,000 completion tokens @ $0.30 = $0.375
    cost = calculate_cost(1_000_000, 1_000_000, "gemini-2.5-flash")
    assert pytest.approx(cost, 0.0001) == 0.375

    # 1,000 prompt tokens + 500 completion tokens
    cost_small = calculate_cost(1000, 500, "gemini-2.5-flash")
    expected = (1000 / 1e6 * 0.075) + (500 / 1e6 * 0.30)
    assert pytest.approx(cost_small, 0.000001) == expected


def test_setup_langsmith_enabled():
    with patch("backend.app.core.telemetry.settings") as mock_settings:
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = "lsv2_test_api_key_123"
        mock_settings.langsmith_project = "AgentForge_Test"
        mock_settings.langsmith_endpoint = "https://api.smith.langchain.com"

        setup_langsmith()

        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGSMITH_TRACING") == "true"
        assert os.environ.get("LANGCHAIN_API_KEY") == "lsv2_test_api_key_123"
        assert os.environ.get("LANGSMITH_PROJECT") == "AgentForge_Test"
        assert is_langsmith_enabled() is True


def test_setup_langsmith_disabled():
    with patch("backend.app.core.telemetry.settings") as mock_settings:
        mock_settings.langsmith_tracing = False
        mock_settings.langsmith_api_key = ""
        mock_settings.langsmith_project = "AgentForge"
        mock_settings.langsmith_endpoint = "https://api.smith.langchain.com"

        with patch.dict(os.environ, {"LANGSMITH_API_KEY": "", "LANGCHAIN_API_KEY": "", "LANGSMITH_TRACING": ""}):
            setup_langsmith()
            assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"
            assert is_langsmith_enabled() is False


def test_agent_traceable_decorator():
    @agent_traceable(name="TestFunction", run_type="chain")
    def sample_func(x: int, y: int) -> int:
        return x + y

    result = sample_func(10, 20)
    assert result == 30


@pytest.mark.asyncio
async def test_base_agent_telemetry_demo_mode():
    db = SessionLocal()
    task = Task(prompt="Test telemetry task", plugin_name="default")
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id
    db.close()

    try:
        agent = BaseAgent(name="TestAgent", system_instruction="Test instruction")
        agent.has_llm = False  # Demo mode

        output = await agent.execute_llm(
            prompt="Write a quick summary of telemetry metrics.",
            task_id=task_id,
            mock_response_content="Mock telemetry response with verified details."
        )

        assert output == "Mock telemetry response with verified details."

        db = SessionLocal()
        logs = db.query(AgentLog).filter(AgentLog.task_id == task_id).all()
        assert len(logs) >= 2  # thinking, output

        output_log = next(l for l in logs if l.log_type == "output")
        assert output_log.prompt_tokens > 0
        assert output_log.completion_tokens > 0
        assert output_log.total_tokens == output_log.prompt_tokens + output_log.completion_tokens
        assert output_log.latency_ms >= 0
        assert output_log.cost_usd >= 0.0
        db.close()
    finally:
        db = SessionLocal()
        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            db.delete(t)
            db.commit()
        db.close()


def test_manager_write_run_summary_telemetry():
    db = SessionLocal()
    task = Task(prompt="Test manager summary task", plugin_name="default")
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    log1 = AgentLog(
        task_id=task_id,
        agent_name="Analyst",
        log_type="output",
        content="Analyst completed research.",
        prompt_tokens=350,
        completion_tokens=420,
        total_tokens=770,
        latency_ms=1200.0,
        cost_usd=0.00015
    )
    db.add(log1)
    db.commit()
    db.close()

    try:
        manager = ManagerAgent()
        manager.write_run_summary(
            task_id=task_id,
            verifier_retry_count=0,
            final_confidence=0.98,
            status="completed",
            agent_sequence=["Planner", "Analyst", "Executor", "Verifier"]
        )

        db = SessionLocal()
        summary_log = (
            db.query(AgentLog)
            .filter(AgentLog.task_id == task_id, AgentLog.log_type == "manager_decision")
            .order_by(AgentLog.id.desc())
            .first()
        )
        assert summary_log is not None
        assert "Manager Run Summary" in summary_log.content
        assert "Observability & Performance Metrics" in summary_log.content
        assert "Total Token Consumption" in summary_log.content
        assert "Total Pipeline Latency" in summary_log.content
        db.close()
    finally:
        db = SessionLocal()
        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            db.delete(t)
            db.commit()
        db.close()
