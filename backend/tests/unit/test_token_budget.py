import pytest
from backend.app.agents.token_budget import compute_token_budget, _detect_tier

def test_detect_tier_keywords():
    assert _detect_tier("comprehensive market analysis and white paper") == "xl"
    assert _detect_tier("research competitor market share and swot analysis") == "large"
    assert _detect_tier("write a python function to refactor stack") == "medium"
    assert _detect_tier("quick list of simple bullet points") == "small"

def test_compute_token_budget_executor():
    # Small tier
    budget_small = compute_token_budget(
        subtask_title="Quick list",
        subtask_desc="simple brief output",
        agent="executor"
    )
    assert budget_small == 1500

    # Large tier
    budget_large = compute_token_budget(
        subtask_title="Market Research",
        subtask_desc="analyze industry competitors and swot matrix",
        agent="executor"
    )
    assert budget_large == 6000

def test_compute_token_budget_override():
    budget = compute_token_budget(override=2048)
    assert budget == 2048

def test_compute_token_budget_agent_caps():
    budget_verifier = compute_token_budget(
        subtask_title="Research analyze",
        subtask_desc="swot matrix report",
        agent="verifier"
    )
    assert budget_verifier == 2000  # Verifier cap for large tier
