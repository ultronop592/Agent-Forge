import pytest
from backend.app.plugins.registry import plugin_registry
from backend.app.plugins.general_analysis import GeneralAnalysisPlugin
from backend.app.plugins.document_qa import DocumentQAPlugin
from backend.app.plugins.code_review import CodeReviewPlugin
from backend.app.agents.planner import PlannerAgent

EXPECTED_PLUGIN_IDS = [
    "software_debugging",
    "startup_research",
    "general_analysis",
    "document_qa",
    "code_review"
]


def test_plugin_registry_contains_all_five_plugins():
    """Verify all 5 plugins are registered and discoverable."""
    plugins = plugin_registry.get_all_plugins()
    assert len(plugins) == 5

    registered_ids = {p.plugin_id for p in plugins}
    for expected_id in EXPECTED_PLUGIN_IDS:
        assert expected_id in registered_ids


def test_plugin_metadata_integrity():
    """Verify all plugins implement required metadata fields."""
    for plugin_id in EXPECTED_PLUGIN_IDS:
        plugin = plugin_registry.get_plugin(plugin_id)
        assert plugin is not None
        assert isinstance(plugin.name, str) and len(plugin.name) > 0
        assert isinstance(plugin.plugin_id, str) and len(plugin.plugin_id) > 0
        assert isinstance(plugin.description, str) and len(plugin.description) > 10


def test_plugin_custom_system_instructions():
    """Verify plugins provide tailored prompts for each workforce agent."""
    agents = ["Planner", "Researcher", "Reasoner", "Executor", "Verifier"]

    for plugin_id in EXPECTED_PLUGIN_IDS:
        plugin = plugin_registry.get_plugin(plugin_id)
        for agent_name in agents:
            instruction = plugin.get_custom_system_instruction(agent_name)
            assert isinstance(instruction, str) and len(instruction) > 20, (
                f"Plugin '{plugin_id}' missing custom system instruction for '{agent_name}'"
            )


def test_plugin_default_subtasks_structure():
    """Verify each plugin returns valid structured subtasks."""
    prompt = "Test deployment objective"

    for plugin_id in EXPECTED_PLUGIN_IDS:
        plugin = plugin_registry.get_plugin(plugin_id)
        subtasks = plugin.get_default_subtasks(prompt)
        assert isinstance(subtasks, list) and len(subtasks) >= 3

        for i, st in enumerate(subtasks):
            assert "title" in st and len(st["title"]) > 0
            assert "description" in st and len(st["description"]) > 0
            assert "assigned_agent" in st and st["assigned_agent"] in ["researcher", "reasoner", "executor", "analyst", "memory_agent", "verifier"]
            assert st.get("order_index") == i


@pytest.mark.asyncio
async def test_planner_agent_integration_with_new_plugins():
    """Verify PlannerAgent generates plan matching each plugin's workflow decomposition."""
    planner = PlannerAgent()
    planner.has_llm = False

    for plugin_id in ["general_analysis", "document_qa", "code_review"]:
        plan = await planner.create_plan(
            prompt="Analyze architectural resilience",
            task_id=f"test-plan-{plugin_id}",
            plugin_name=plugin_id
        )
        assert plan is not None
        assert len(plan.subtasks) == 3
        assert "workflow plugin" in plan.reasoning
        # Subtasks should have valid titles and agents
        assigned = [s.assigned_agent for s in plan.subtasks]
        assert "researcher" in assigned
        assert "reasoner" in assigned
        assert "executor" in assigned
