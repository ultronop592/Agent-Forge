import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.agent_config import (
    agent_config_registry,
    AVAILABLE_MODELS,
    DEFAULT_AGENT_CONFIGS
)
from backend.app.agents.executor import ExecutorAgent

client = TestClient(app)


def test_agent_config_registry_defaults():
    agent_config_registry.reset()
    cfg = agent_config_registry.get_agent_config("Executor")
    assert cfg["model"] == "gemini-2.5-flash"
    assert cfg["temperature"] == 0.2
    assert cfg["token_budget"] == 6000


def test_agent_config_registry_update_and_override():
    agent_config_registry.reset()
    # Update global model
    agent_config_registry.update_agent_config("global", {"model": "gemini-2.5-pro", "temperature": 0.5})
    # Planner inherits global model unless overridden
    planner_cfg = agent_config_registry.get_agent_config("Planner")
    assert planner_cfg["model"] == "gemini-2.5-pro"

    # Specific override on Executor
    agent_config_registry.update_agent_config("Executor", {"temperature": 0.0, "token_budget": 8000})
    exec_cfg = agent_config_registry.get_agent_config("Executor")
    assert exec_cfg["temperature"] == 0.0
    assert exec_cfg["token_budget"] == 8000
    assert exec_cfg["model"] == "gemini-2.5-pro"

    # Reset
    agent_config_registry.reset()
    assert agent_config_registry.get_temperature("Executor") == 0.2


def test_api_agents_config_get_and_put():
    agent_config_registry.reset()
    # 1. GET /api/agents/config
    res = client.get("/api/agents/config")
    assert res.status_code == 200
    data = res.json()
    assert "configs" in data
    assert "available_models" in data
    assert len(data["available_models"]) >= 4

    # 2. PUT /api/agents/config/Analyst
    update_res = client.put(
        "/api/agents/config/Analyst",
        json={"model": "gemini-2.5-pro", "temperature": 0.4, "token_budget": 5000}
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()["config"]
    assert updated_data["model"] == "gemini-2.5-pro"
    assert updated_data["temperature"] == 0.4
    assert updated_data["token_budget"] == 5000

    # 3. GET /api/agents shows attached config
    list_res = client.get("/api/agents")
    assert list_res.status_code == 200
    analyst_card = next(a for a in list_res.json() if a["name"] == "Analyst")
    assert analyst_card["config"]["model"] == "gemini-2.5-pro"

    # 4. POST /api/agents/config/reset
    reset_res = client.post("/api/agents/config/reset")
    assert reset_res.status_code == 200
    assert agent_config_registry.get_model("Analyst") == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_base_agent_uses_dynamic_config():
    agent_config_registry.reset()
    agent_config_registry.update_agent_config("Executor", {
        "model": "gemini-2.5-pro",
        "temperature": 0.75,
        "token_budget": 1200,
        "custom_instruction": "Strict JSON output only."
    })

    executor = ExecutorAgent()
    executor.has_llm = True
    executor.client = AsyncMock()

    captured_config = None
    captured_model = None

    async def mock_stream(prompt, config, model=None):
        nonlocal captured_config, captured_model
        captured_config = config
        captured_model = model
        yield type("Chunk", (), {"text": "output", "usage_metadata": None})()

    with patch.object(executor, "_stream_content", side_effect=mock_stream):
        await executor.execute_llm(prompt="test", task_id="t1", subtask_id="s1")

    assert captured_config is not None
    assert captured_config.temperature == 0.75
    assert captured_config.max_output_tokens == 1200
    assert "[USER DIRECTIVE FOR EXECUTOR]:\nStrict JSON output only." in captured_config.system_instruction
    assert captured_model == "gemini-2.5-pro"

    agent_config_registry.reset()
