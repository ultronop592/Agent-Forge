import logging
from typing import Dict, Any, List, Literal
from langgraph.graph import StateGraph, END

from backend.app.workflows.state import AgentState
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.researcher import ResearcherAgent
from backend.app.agents.reasoner import ReasonerAgent
from backend.app.agents.executor import ExecutorAgent
from backend.app.agents.verifier import VerifierAgent
from backend.app.agents.memory_agent import MemoryAgent
from backend.app.agents.manager_agent import ManagerAgent, _MAX_AGENT_RETRIES

from backend.app.database.connection import SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog

logger = logging.getLogger("agentforge.workflows")

# ---------------------------------------------------------------------------
# Context truncation helpers
# ---------------------------------------------------------------------------
_EXECUTOR_CONTEXT_CHAR_LIMIT = 8_000
_REASONER_CONTEXT_CHAR_LIMIT = 12_000


def _truncate_context(context: str, char_limit: int, label: str) -> str:
    """Truncate context to char_limit, appending a notice when trimmed."""
    if len(context) <= char_limit:
        return context
    trimmed = context[:char_limit]
    last_newline = trimmed.rfind("\n")
    if last_newline > char_limit * 0.8:
        trimmed = trimmed[:last_newline]
    trimmed += (
        f"\n\n[⚠️ {label} context truncated to {char_limit:,} chars for efficiency. "
        "Full outputs are stored in agent state.]"
    )
    logger.info(f"Context for {label} truncated from {len(context):,} → {len(trimmed):,} chars.")
    return trimmed


# ---------------------------------------------------------------------------
# Agent instances
# ---------------------------------------------------------------------------
planner_agent   = PlannerAgent()
researcher_agent = ResearcherAgent()
reasoner_agent  = ReasonerAgent()
executor_agent  = ExecutorAgent()
verifier_agent  = VerifierAgent()
memory_agent    = MemoryAgent()
manager_agent   = ManagerAgent()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def update_subtask_in_db(subtask_id: str, status: str, output: str = None, confidence_score: float = None):
    db = SessionLocal()
    try:
        sub = db.query(Subtask).filter(Subtask.id == subtask_id).first()
        if sub:
            sub.status = status
            if output is not None:
                sub.output = output
            if confidence_score is not None:
                sub.confidence_score = confidence_score
            db.commit()
    except Exception as e:
        logger.error(f"Error updating subtask status: {e}")
    finally:
        db.close()


def update_task_in_db(task_id: str, status: str, final_result: str = None):
    db = SessionLocal()
    try:
        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            t.status = status
            if final_result is not None:
                t.final_result = final_result
            db.commit()
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Worker agent nodes
# ---------------------------------------------------------------------------
async def planner_node(state: AgentState) -> Dict[str, Any]:
    task_id = state["task_id"]
    prompt  = state["prompt"]

    update_task_in_db(task_id, "running")

    plan = await planner_agent.create_plan(prompt, task_id)

    db = SessionLocal()
    subtask_dicts = []
    try:
        for idx, sub in enumerate(plan.subtasks):
            db_sub = Subtask(
                task_id=task_id,
                title=sub.title,
                description=sub.description,
                assigned_agent=sub.assigned_agent,
                status="pending",
                order_index=idx
            )
            db.add(db_sub)
            db.commit()
            db.refresh(db_sub)
            subtask_dicts.append(db_sub.to_dict())
    except Exception as e:
        logger.error(f"Error saving subtasks: {e}")
    finally:
        db.close()

    return {
        "subtasks": subtask_dicts,
        "current_subtask_index": 0,
        "agent_outputs": {},
        "logs": []
    }


async def researcher_node(state: AgentState) -> Dict[str, Any]:
    task_id  = state["task_id"]
    idx      = state["current_subtask_index"]
    subtask  = state["subtasks"][idx]
    subtask_id = subtask["id"]

    update_subtask_in_db(subtask_id, "running")

    output = await researcher_agent.run_subtask(
        subtask_title=subtask["title"],
        subtask_desc=subtask["description"],
        task_id=task_id,
        subtask_id=subtask_id
    )

    update_subtask_in_db(subtask_id, "completed", output=output)

    outputs = state["agent_outputs"].copy()
    outputs[subtask_id] = output

    return {
        "agent_outputs": outputs,
        # NOTE: current_subtask_index is NOT incremented here.
        # The Manager node decides whether to advance or retry.
        "_last_worker": "researcher",
        "_last_subtask_id": subtask_id,
    }


async def reasoner_node(state: AgentState) -> Dict[str, Any]:
    task_id    = state["task_id"]
    idx        = state["current_subtask_index"]
    subtask    = state["subtasks"][idx]
    subtask_id = subtask["id"]

    update_subtask_in_db(subtask_id, "running")

    prev_context_full = "\n\n".join([
        f"--- Subtask: {sub['title']} ---\n{output}"
        for sub_id, output in state["agent_outputs"].items()
        for sub in state["subtasks"] if sub["id"] == sub_id
    ])
    prev_context = _truncate_context(prev_context_full, _REASONER_CONTEXT_CHAR_LIMIT, "Reasoner")

    output = await reasoner_agent.run_subtask(
        subtask_title=subtask["title"],
        subtask_desc=subtask["description"],
        previous_outputs=prev_context,
        task_id=task_id,
        subtask_id=subtask_id
    )

    update_subtask_in_db(subtask_id, "completed", output=output)

    outputs = state["agent_outputs"].copy()
    outputs[subtask_id] = output

    return {
        "agent_outputs": outputs,
        "_last_worker": "reasoner",
        "_last_subtask_id": subtask_id,
    }


async def executor_node(state: AgentState) -> Dict[str, Any]:
    task_id = state["task_id"]
    idx     = state["current_subtask_index"]

    if idx >= len(state["subtasks"]):
        exec_subs = [s for s in state["subtasks"] if s["assigned_agent"] == "executor"]
        subtask   = exec_subs[-1] if exec_subs else state["subtasks"][-1]
    else:
        subtask = state["subtasks"][idx]

    subtask_id = subtask["id"]

    update_subtask_in_db(subtask_id, "running")

    context_full = "\n\n".join([
        f"--- Context: {sub['title']} ---\n{output}"
        for sub_id, output in state["agent_outputs"].items()
        for sub in state["subtasks"] if sub["id"] == sub_id
    ])
    context = _truncate_context(context_full, _EXECUTOR_CONTEXT_CHAR_LIMIT, "Executor")

    feedback = state.get("verifier_feedback", "")
    output = await executor_agent.run_subtask(
        subtask_title=subtask["title"],
        subtask_desc=subtask["description"],
        context=context,
        task_id=task_id,
        subtask_id=subtask_id,
        verifier_feedback=feedback
    )

    update_subtask_in_db(subtask_id, "completed", output=output)

    outputs = state["agent_outputs"].copy()
    outputs[subtask_id] = output

    new_idx = idx if idx >= len(state["subtasks"]) else idx + 1

    return {
        "agent_outputs": outputs,
        "current_subtask_index": new_idx,
        "_last_worker": "executor",
        "_last_subtask_id": subtask_id,
    }


async def memory_node(state: AgentState) -> Dict[str, Any]:
    task_id    = state["task_id"]
    idx        = state["current_subtask_index"]
    subtask    = state["subtasks"][idx]
    subtask_id = subtask["id"]

    update_subtask_in_db(subtask_id, "running")

    output = await memory_agent.run_subtask(
        subtask_title=subtask["title"],
        subtask_desc=subtask["description"],
        task_id=task_id,
        subtask_id=subtask_id
    )

    update_subtask_in_db(subtask_id, "completed", output=output)

    outputs = state["agent_outputs"].copy()
    outputs[subtask_id] = output

    return {
        "agent_outputs": outputs,
        "current_subtask_index": idx + 1
    }


# ---------------------------------------------------------------------------
# Manager node — sits after every worker agent except Memory & Verifier
# ---------------------------------------------------------------------------
async def manager_node(state: AgentState) -> Dict[str, Any]:
    task_id       = state["task_id"]
    last_worker   = state.get("_last_worker", "executor")
    subtask_id    = state.get("_last_subtask_id")

    # Retrieve the subtask being evaluated
    subtask = next(
        (s for s in state["subtasks"] if s["id"] == subtask_id),
        state["subtasks"][state["current_subtask_index"] - 1]
    ) if subtask_id else state["subtasks"][state.get("current_subtask_index", 1) - 1]

    output = state["agent_outputs"].get(subtask_id or "", "")

    # ── Evaluate quality ────────────────────────────────────────────────
    result = await manager_agent.evaluate_agent_output(
        agent_name=last_worker,
        subtask_title=subtask["title"],
        subtask_desc=subtask["description"],
        output=output,
        task_id=task_id,
        subtask_id=subtask_id,
    )

    # ── Update tracking state ────────────────────────────────────────────
    quality_scores = dict(state.get("manager_quality_scores", {}))
    skip_flags     = dict(state.get("manager_skip_flags", {}))
    retry_counts   = dict(state.get("agent_retry_counts", {}))

    sid_key = subtask_id or subtask["id"]
    quality_scores[sid_key] = result.score

    current_retries = retry_counts.get(sid_key, 0)

    if result.passed:
        # ✅ Advance pipeline
        manager_agent.log_transition(
            task_id=task_id,
            from_agent=last_worker,
            to_agent="next_in_pipeline",
            quality_score=result.score,
            decision="PASS — advancing",
        )
        # Advance the subtask index for researcher & reasoner
        # (executor already increments its own index before reaching manager)
        new_idx = state["current_subtask_index"]
        if last_worker in ("researcher", "reasoner"):
            new_idx = state["current_subtask_index"] + 1

        return {
            "manager_quality_scores": quality_scores,
            "manager_skip_flags": skip_flags,
            "agent_retry_counts": retry_counts,
            "current_subtask_index": new_idx,
        }

    elif current_retries < _MAX_AGENT_RETRIES:
        # ❌ Retry the same agent
        retry_counts[sid_key] = current_retries + 1
        msg = (
            f"[Manager] {last_worker} FAILED quality gate "
            f"(score={result.score:.2f}, attempt {current_retries + 1}/{_MAX_AGENT_RETRIES}). "
            f"Retrying with hint: {result.correction_hint}"
        )
        manager_agent.log_db(task_id, subtask_id, "manager_decision", msg)
        logger.warning(msg)

        # Re-inject correction hint as verifier_feedback so Executor can use it too
        extra = {}
        if last_worker == "executor":
            extra["verifier_feedback"] = result.correction_hint

        return {
            "manager_quality_scores": quality_scores,
            "manager_skip_flags": skip_flags,
            "agent_retry_counts": retry_counts,
            **extra,
        }

    else:
        # ❌ Max retries exhausted — skip and advance
        skip_flags[sid_key] = True
        msg = (
            f"[Manager] {last_worker} exceeded max retries "
            f"({_MAX_AGENT_RETRIES}). Skipping subtask and advancing pipeline."
        )
        manager_agent.log_db(task_id, subtask_id, "manager_decision", msg)
        logger.warning(msg)

        new_idx = state["current_subtask_index"]
        if last_worker in ("researcher", "reasoner"):
            new_idx += 1

        return {
            "manager_quality_scores": quality_scores,
            "manager_skip_flags": skip_flags,
            "agent_retry_counts": retry_counts,
            "current_subtask_index": new_idx,
        }


# ---------------------------------------------------------------------------
# Verifier node
# ---------------------------------------------------------------------------
async def verifier_node(state: AgentState) -> Dict[str, Any]:
    task_id     = state["task_id"]
    prompt      = state["prompt"]
    retry_count = state.get("retry_count", 0)

    executor_outputs = []
    for sub in state["subtasks"]:
        sub_id = sub["id"]
        if sub["assigned_agent"] == "executor" and sub_id in state["agent_outputs"]:
            executor_outputs.append(state["agent_outputs"][sub_id])

    exec_content = (
        "\n\n".join(executor_outputs)
        if executor_outputs
        else "\n\n".join(state["agent_outputs"].values())
    )

    verifier_agent.log_db(task_id, None, "thinking",
                          f"Starting final verification checks (Attempt {retry_count + 1})...")
    result = await verifier_agent.verify_output(
        original_goal=prompt,
        generated_output=exec_content,
        task_id=task_id,
        subtask_id=None
    )

    if not result.is_valid and retry_count < 3:
        msg = (
            f"🛡️ [Self-Healing] Verification failed (score: {result.confidence_score:.2f}). "
            f"Feedback: {result.feedback}\n"
            f"Routing back to Executor (Attempt {retry_count + 1}/3)..."
        )
        verifier_agent.log_db(task_id, None, "thinking", msg)
        logger.warning(msg)

        for sub in state["subtasks"]:
            if sub["assigned_agent"] == "verifier":
                update_subtask_in_db(sub["id"], "running",
                                     output=f"Verification failed. Feedback: {result.feedback}")

        return {
            "verification_results": {
                "is_valid":         result.is_valid,
                "confidence_score": result.confidence_score,
                "feedback":         result.feedback
            },
            "verifier_feedback": result.feedback,
            "retry_count":       retry_count + 1,
        }

    # ── Task complete ────────────────────────────────────────────────────
    memory_agent.store_memory(
        content=(
            f"Learned from goal '{prompt[:80]}...': "
            f"Verification Confidence Score: {result.confidence_score:.2f}. "
            f"Key observations: {result.feedback}"
        ),
        category="factual"
    )

    status = "completed" if result.is_valid else "failed"
    update_task_in_db(task_id, status, final_result=result.verified_output)

    for sub in state["subtasks"]:
        if sub["assigned_agent"] == "verifier":
            update_subtask_in_db(sub["id"], status,
                                 output=result.verified_output,
                                 confidence_score=result.confidence_score)

    # ── Manager writes run summary ───────────────────────────────────────
    manager_agent.write_run_summary(
        task_id=task_id,
        quality_scores=state.get("manager_quality_scores", {}),
        agent_retry_counts=state.get("agent_retry_counts", {}),
        verifier_retry_count=retry_count,
        final_confidence=result.confidence_score,
        status=status,
    )

    return {
        "verification_results": {
            "is_valid":         result.is_valid,
            "confidence_score": result.confidence_score,
            "feedback":         result.feedback
        },
        "verifier_feedback": "",
        "final_result":      result.verified_output,
    }


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------
def route_after_planner(state: AgentState) -> Literal[
    "researcher", "reasoner", "executor", "memory_agent", "verifier", "__end__"
]:
    """Route the first subtask from the Planner."""
    return _pick_next_agent(state)


def route_after_manager(state: AgentState) -> Literal[
    "researcher", "reasoner", "executor", "memory_agent", "verifier", "__end__"
]:
    """
    After a Manager gate:
    - If the Manager decided to retry → re-route to same worker agent.
    - Otherwise → advance to next agent in the pipeline.
    """
    last_worker = state.get("_last_worker", "executor")
    subtask_id  = state.get("_last_subtask_id")
    retry_counts = state.get("agent_retry_counts", {})
    skip_flags   = state.get("manager_skip_flags", {})

    # Check if this subtask is still being retried (retry incremented but index not advanced)
    if subtask_id:
        retries  = retry_counts.get(subtask_id, 0)
        skipped  = skip_flags.get(subtask_id, False)
        quality  = state.get("manager_quality_scores", {}).get(subtask_id, 1.0)
        from backend.app.agents.manager_agent import _QUALITY_THRESHOLDS
        threshold = _QUALITY_THRESHOLDS.get(last_worker, _QUALITY_THRESHOLDS["default"])

        # If quality failed AND retries < max AND not skipped → retry same agent
        if quality < threshold and retries > 0 and retries <= _MAX_AGENT_RETRIES and not skipped:
            return last_worker  # type: ignore[return-value]

    # Otherwise advance normally
    return _pick_next_agent(state)


def route_after_memory(state: AgentState) -> Literal[
    "researcher", "reasoner", "executor", "memory_agent", "verifier", "__end__"
]:
    return _pick_next_agent(state)


def route_verifier_output(state: AgentState) -> Literal["executor", "__end__"]:
    v_res       = state.get("verification_results", {})
    retry_count = state.get("retry_count", 0)
    if v_res and not v_res.get("is_valid", True) and retry_count < 3:
        return "executor"
    return "__end__"


def _pick_next_agent(state: AgentState) -> Literal[
    "researcher", "reasoner", "executor", "memory_agent", "verifier", "__end__"
]:
    idx      = state["current_subtask_index"]
    subtasks = state["subtasks"]

    if idx >= len(subtasks):
        return "verifier"

    agent = subtasks[idx]["assigned_agent"]
    if agent == "researcher":
        return "researcher"
    elif agent == "reasoner":
        return "reasoner"
    elif agent == "executor":
        return "executor"
    elif agent == "memory_agent":
        return "memory_agent"
    elif agent == "verifier":
        return "verifier"
    return "executor"


# ---------------------------------------------------------------------------
# Build and compile graph
# ---------------------------------------------------------------------------
builder = StateGraph(AgentState)

# Register nodes
builder.add_node("planner",     planner_node)
builder.add_node("researcher",  researcher_node)
builder.add_node("reasoner",    reasoner_node)
builder.add_node("executor",    executor_node)
builder.add_node("memory_agent", memory_node)
builder.add_node("manager",     manager_node)     # ← new supervisor node
builder.add_node("verifier",    verifier_node)

# Entry point
builder.set_entry_point("planner")

# Planner → first agent
builder.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "researcher":  "researcher",
        "reasoner":    "reasoner",
        "executor":    "executor",
        "memory_agent": "memory_agent",
        "verifier":    "verifier",
    }
)

# Worker agents → Manager gate (except Executor which is handled specially)
builder.add_edge("researcher", "manager")
builder.add_edge("reasoner",   "manager")

# Executor already increments the index, so it also feeds through Manager
builder.add_edge("executor", "manager")

# Manager → next agent (or retry same agent)
_AGENT_MAP = {
    "researcher":  "researcher",
    "reasoner":    "reasoner",
    "executor":    "executor",
    "memory_agent": "memory_agent",
    "verifier":    "verifier",
    "__end__":     END,
}
builder.add_conditional_edges("manager", route_after_manager, _AGENT_MAP)

# Memory bypasses Manager (no quality gate needed for retrieval)
builder.add_conditional_edges("memory_agent", route_after_memory, _AGENT_MAP)

# Verifier → self-heal loop or end
builder.add_conditional_edges(
    "verifier",
    route_verifier_output,
    {
        "executor": "executor",
        "__end__":  END,
    }
)

orchestrator_graph = builder.compile()
