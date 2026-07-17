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
    retry_count: int           # Verifier → Executor self-healing retries
    verifier_feedback: str
    prompt_embedding: List[float]  # Cached embedding of the prompt
    agent_sequence: List[str]      # Manager tracks execution order for run summary
    # ── Manager/QA Agent tracking ────────────────────────────────────────
    manager_quality_scores: Dict[str, float]   # subtask_id → quality score from QA Agent
    manager_skip_flags: Dict[str, bool]        # subtask_id → True if skipped after max retries
    agent_retry_counts: Dict[str, int]         # subtask_id → individual agent retries by Manager


