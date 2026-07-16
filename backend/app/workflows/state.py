from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    task_id: str
    prompt: str
    plugin_name: str
    subtasks: List[Dict[str, Any]]
    current_subtask_index: int
    agent_outputs: Dict[str, str]
    verification_results: Dict[str, Any]
    final_result: str
    retry_count: int
    verifier_feedback: str
