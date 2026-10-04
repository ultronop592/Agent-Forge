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


def test_configurable_cost_model():
    from backend.app.core.config import settings

    # Default should be gemini-2.5-flash
    assert settings.cost_model == "gemini-2.5-flash"

    # calculate_cost with no model argument uses settings.cost_model
    cost_default = calculate_cost(1_000_000, 1_000_000)
    assert pytest.approx(cost_default, 0.0001) == 0.375

    # calculate_cost with explicit gemini-1.5-pro (1.25 + 5.00 = 6.25)
    cost_pro = calculate_cost(1_000_000, 1_000_000, model="gemini-1.5-pro")
    assert pytest.approx(cost_pro, 0.0001) == 6.25

    # BaseAgent initializes self.cost_model from settings/env var
    agent = BaseAgent(name="CostTestAgent", system_instruction="Testing cost")
    assert agent.cost_model == "gemini-2.5-flash"

    # BaseAgent with overridden cost_model
    with patch.object(settings, "cost_model", "gemini-1.5-pro"):
        agent_pro = BaseAgent(name="CostTestPro", system_instruction="Testing pro cost")
        assert agent_pro.cost_model == "gemini-1.5-pro"


def test_setup_langsmith_enabled():
    with patch.dict(os.environ, {"LANGSMITH_API_KEY": "", "LANGCHAIN_API_KEY": "", "LANGSMITH_TRACING": "", "LANGCHAIN_TRACING_V2": "", "LANGSMITH_PROJECT": "", "LANGCHAIN_PROJECT": ""}, clear=False):
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


def test_task_to_dict_no_double_counting():
    """
    Ensure Task.to_dict() accurately sums metrics without doubling them
    when both 'output' and 'telemetry' logs exist for an agent execution.
    """
    task = Task(id="test-task-no-double", prompt="Test double counting", plugin_name="default")

    # Simulate an agent execution with both 'output' and legacy duplicate 'telemetry' logs
    log_output = AgentLog(
        task_id=task.id,
        agent_name="Analyst",
        log_type="output",
        content="Research findings here.",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=450.0,
        cost_usd=0.0001
    )
    log_telemetry = AgentLog(
        task_id=task.id,
        agent_name="Analyst",
        log_type="telemetry",
        content="📊 [Analyst Metrics] Latency: 450.0ms | Tokens: 150 | Est. Cost: $0.000100",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=450.0,
        cost_usd=0.0001
    )
    task.logs = [log_output, log_telemetry]

    d = task.to_dict()

    # Must be 150, NOT 300
    assert d["total_tokens"] == 150
    # Must be 0.0001, NOT 0.0002
    assert d["total_cost_usd"] == 0.0001
    # Must be 450.0, NOT 900.0
    assert d["total_latency_ms"] == 450.0


def test_task_to_dict_multi_agent_pipeline():
    """
    Ensure multi-agent pipeline logs (Planner + Analyst + Verifier)
    sum each agent's execution once without double counting.
    """
    task = Task(id="test-task-multi-agent", prompt="Multi-agent pipeline", plugin_name="default")

    logs = []
    agent_metrics = [
        ("Planner", 100, 50, 150, 300.0, 0.00005),
        ("Analyst", 200, 100, 300, 600.0, 0.00010),
        ("Verifier", 80, 40, 120, 200.0, 0.00004),
    ]

    for name, p_tok, c_tok, tot_tok, lat, cost in agent_metrics:
        # Output log
        logs.append(AgentLog(
            task_id=task.id,
            agent_name=name,
            log_type="output",
            content=f"{name} completed work.",
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            total_tokens=tot_tok,
            latency_ms=lat,
            cost_usd=cost
        ))
        # Telemetry log
        logs.append(AgentLog(
            task_id=task.id,
            agent_name=name,
            log_type="telemetry",
            content=f"📊 [{name} Metrics] Latency: {lat}ms | Tokens: {tot_tok}",
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            total_tokens=tot_tok,
            latency_ms=lat,
            cost_usd=cost
        ))

    task.logs = logs
    d = task.to_dict()

    expected_tokens = 150 + 300 + 120  # 570
    expected_latency = 300.0 + 600.0 + 200.0  # 1100.0
    expected_cost = round(0.00005 + 0.00010 + 0.00004, 6)  # 0.00019

    assert d["total_tokens"] == expected_tokens
    assert d["total_latency_ms"] == expected_latency
    assert d["total_cost_usd"] == expected_cost


def test_task_to_dict_fallbacks():
    """
    Ensure fallbacks work gracefully:
    1. Legacy data with only 'telemetry' logs
    2. Stored Task column values when logs is empty
    3. Blank task with no metrics
    """
    # 1. Telemetry-only legacy logs
    t1 = Task(id="test-legacy", prompt="Legacy task", plugin_name="default")
    t1.logs = [
        AgentLog(
            task_id=t1.id,
            agent_name="Executor",
            log_type="telemetry",
            content="📊 Telemetry",
            prompt_tokens=40,
            completion_tokens=60,
            total_tokens=100,
            latency_ms=250.0,
            cost_usd=0.00005
        )
    ]
    d1 = t1.to_dict()
    assert d1["total_tokens"] == 100
    assert d1["total_cost_usd"] == 0.00005
    assert d1["total_latency_ms"] == 250.0

    # 2. Stored Task columns without logs loaded
    t2 = Task(
        id="test-stored",
        prompt="Stored columns task",
        plugin_name="default",
        total_tokens=450,
        total_cost_usd=0.0003,
        total_latency_ms=800.0
    )
    t2.logs = []
    d2 = t2.to_dict()
    assert d2["total_tokens"] == 450
    assert d2["total_cost_usd"] == 0.0003
    assert d2["total_latency_ms"] == 800.0

    # 3. Blank task
    t3 = Task(id="test-blank", prompt="Blank task", plugin_name="default")
    t3.logs = []
    d3 = t3.to_dict()
    assert d3["total_tokens"] == 0
    assert d3["total_cost_usd"] == 0.0
    assert d3["total_latency_ms"] == 0.0


def test_orchestrator_update_task_in_db_no_double_counting():
    """
    Ensure orchestrator.update_task_in_db stores single-counted metrics in the DB.
    """
    from backend.app.workflows.orchestrator import update_task_in_db

    db = SessionLocal()
    task = Task(prompt="Test orchestrator DB update", plugin_name="default")
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    # Add output log (150 tokens) and telemetry log (150 tokens)
    log_out = AgentLog(
        task_id=task_id,
        agent_name="Analyst",
        log_type="output",
        content="Analyst output",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=300.0,
        cost_usd=0.0001
    )
    log_tel = AgentLog(
        task_id=task_id,
        agent_name="Analyst",
        log_type="telemetry",
        content="📊 Analyst Telemetry",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        latency_ms=300.0,
        cost_usd=0.0001
    )
    db.add(log_out)
    db.add(log_tel)
    db.commit()
    db.close()

    try:
        update_task_in_db(task_id, status="completed", final_result="Done.")

        db = SessionLocal()
        saved_task = db.query(Task).filter(Task.id == task_id).first()
        assert saved_task is not None
        assert saved_task.total_tokens == 150
        assert saved_task.total_latency_ms == 300.0
        assert pytest.approx(saved_task.total_cost_usd, 0.000001) == 0.0001
        db.close()
    finally:
        db = SessionLocal()
        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            db.delete(t)
            db.commit()
        db.close()

