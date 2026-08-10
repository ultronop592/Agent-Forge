import pytest
from backend.app.workflows.orchestrator import route_subtasks, route_verifier_output
from backend.app.workflows.state import AgentState

def test_route_subtasks_parallel_research():
    state: AgentState = {
        "task_id": "t1",
        "prompt": "test",
        "plugin_name": "default",
        "subtasks": [
            {"id": "s1", "assigned_agent": "memory_agent"},
            {"id": "s2", "assigned_agent": "analyst"},
            {"id": "s3", "assigned_agent": "executor"}
        ],
        "current_subtask_index": 0,
        "agent_outputs": {},
        "verification_results": {},
        "final_result": "",
        "retry_count": 0,
        "verifier_feedback": "",
        "prompt_embedding": [],
        "agent_sequence": [],
        "manager_quality_scores": {},
        "manager_skip_flags": {},
        "agent_retry_counts": {}
    }
    # 2 consecutive research agents -> should route to parallel_research
    assert route_subtasks(state) == "parallel_research"

def test_route_subtasks_end_triggers_verifier():
    state: AgentState = {
        "task_id": "t1",
        "prompt": "test",
        "plugin_name": "default",
        "subtasks": [
            {"id": "s1", "assigned_agent": "executor"}
        ],
        "current_subtask_index": 1, # Index at end of subtasks
        "agent_outputs": {},
        "verification_results": {},
        "final_result": "",
        "retry_count": 0,
        "verifier_feedback": "",
        "prompt_embedding": [],
        "agent_sequence": [],
        "manager_quality_scores": {},
        "manager_skip_flags": {},
        "agent_retry_counts": {}
    }
    assert route_subtasks(state) == "verifier"

def test_route_verifier_output_loopback():
    state: AgentState = {
        "task_id": "t1",
        "prompt": "test",
        "plugin_name": "default",
        "subtasks": [],
        "current_subtask_index": 0,
        "agent_outputs": {},
        "verification_results": {"is_valid": False},
        "final_result": "",
        "retry_count": 1,
        "verifier_feedback": "Fix syntax error",
        "prompt_embedding": [],
        "agent_sequence": [],
        "manager_quality_scores": {},
        "manager_skip_flags": {},
        "agent_retry_counts": {}
    }
    # Should route back to executor for retry
    assert route_verifier_output(state) == "executor"

def test_route_verifier_output_end():
    state: AgentState = {
        "task_id": "t1",
        "prompt": "test",
        "plugin_name": "default",
        "subtasks": [],
        "current_subtask_index": 0,
        "agent_outputs": {},
        "verification_results": {"is_valid": True},
        "final_result": "Success",
        "retry_count": 0,
        "verifier_feedback": "",
        "prompt_embedding": [],
        "agent_sequence": [],
        "manager_quality_scores": {},
        "manager_skip_flags": {},
        "agent_retry_counts": {}
    }
    assert route_verifier_output(state) == "__end__"
