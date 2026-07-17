import logging
from typing import Dict, Any, List, Literal
from langgraph.graph import StateGraph, END

from backend.app.workflows.state import AgentState
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.analyst_agent import AnalystAgent
from backend.app.agents.executor import ExecutorAgent
from backend.app.agents.verifier import VerifierAgent
from backend.app.agents.memory_agent import MemoryAgent
from backend.app.agents.manager_agent import ManagerAgent

from backend.app.database.connection import SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog

logger = logging.getLogger("agentforge.workflows")

# ---------------------------------------------------------------------------
# Context truncation helpers
# ---------------------------------------------------------------------------
_EXECUTOR_CONTEXT_CHAR_LIMIT = 8_000


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
analyst_agent   = AnalystAgent()
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
# Stage nodes
# ---------------------------------------------------------------------------
async def planner_node(state: AgentState) -> Dict[str, Any]:
    task_id = state["task_id"]
    prompt  = state["prompt"]

    update_task_in_db(task_id, "running")

    manager_agent.log_db(task_id, None, "manager_decision",
        "🧭 [Manager] Workforce activated. Delegating to **Planner** to decompose the goal into subtasks.")

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

    # Manager announces the full execution plan
    manager_agent.log_plan_received(
        task_id=task_id,
        subtask_count=len(subtask_dicts),
        subtask_titles=[s["title"] for s in subtask_dicts],
    )
    manager_agent.log_transition(task_id, "Planner", "Router", reason="plan accepted, dispatching subtasks")

    return {
        "subtasks": subtask_dicts,
        "current_subtask_index": 0,
        "agent_outputs": {},
        "agent_sequence": ["Planner"],
        "logs": []
    }


async def memory_node(state: AgentState) -> Dict[str, Any]:
    task_id    = state["task_id"]
    idx        = state["current_subtask_index"]
    subtask    = state["subtasks"][idx]
    subtask_id = subtask["id"]

    manager_agent.announce_start(task_id, "Memory", subtask["title"], subtask_id)
    update_subtask_in_db(subtask_id, "running")

    # Call memory agent — it returns (output, prompt_embedding)
    output, query_vector = await memory_agent.run_subtask(
        subtask_title=subtask["title"],
        subtask_desc=subtask["description"],
        task_id=task_id,
        subtask_id=subtask_id
    )

    update_subtask_in_db(subtask_id, "completed", output=output)
    manager_agent.announce_complete(task_id, "Memory", subtask["title"], subtask_id)

    outputs = state["agent_outputs"].copy()
    outputs[subtask_id] = output
    seq = state.get("agent_sequence", []) + ["Memory"]

    return {
        "agent_outputs": outputs,
        "current_subtask_index": idx + 1,
        "prompt_embedding": query_vector,
        "agent_sequence": seq,
    }


async def analyst_node(state: AgentState) -> Dict[str, Any]:
    task_id    = state["task_id"]
    idx        = state["current_subtask_index"]
    subtask    = state["subtasks"][idx]
    subtask_id = subtask["id"]

    manager_agent.announce_start(task_id, "Analyst", subtask["title"], subtask_id)
    update_subtask_in_db(subtask_id, "running")

    # Single-step Search + Reasoning
    output = await analyst_agent.run_subtask(
        subtask_title=subtask["title"],
        subtask_desc=subtask["description"],
        task_id=task_id,
        subtask_id=subtask_id
    )

    update_subtask_in_db(subtask_id, "completed", output=output)
    manager_agent.announce_complete(task_id, "Analyst", subtask["title"], subtask_id)

    outputs = state["agent_outputs"].copy()
    outputs[subtask_id] = output
    seq = state.get("agent_sequence", []) + ["Analyst"]

    return {
        "agent_outputs": outputs,
        "current_subtask_index": idx + 1,
        "agent_sequence": seq,
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

    manager_agent.announce_start(task_id, "Executor", subtask["title"], subtask_id)
    update_subtask_in_db(subtask_id, "running")

    # Gather prior context
    context_full = "\n\n".join([
        f"--- Context: {sub['title']} ---\n{output}"
        for sub_id, output in state["agent_outputs"].items()
        for sub in state["subtasks"] if sub["id"] == sub_id
    ])
    context = _truncate_context(context_full, _EXECUTOR_CONTEXT_CHAR_LIMIT, "Executor")

    feedback = state.get("verifier_feedback", "")
    if feedback:
        manager_agent.log_db(task_id, subtask_id, "manager_decision",
            f"📌 [Manager] Passing Verifier correction hint to Executor:\n   └─ {feedback}")

    output = await executor_agent.run_subtask(
        subtask_title=subtask["title"],
        subtask_desc=subtask["description"],
        context=context,
        task_id=task_id,
        subtask_id=subtask_id,
        verifier_feedback=feedback
    )

    update_subtask_in_db(subtask_id, "completed", output=output)
    manager_agent.announce_complete(task_id, "Executor", subtask["title"], subtask_id)

    outputs = state["agent_outputs"].copy()
    outputs[subtask_id] = output
    seq = state.get("agent_sequence", []) + ["Executor"]

    new_idx = idx if idx >= len(state["subtasks"]) else idx + 1

    return {
        "agent_outputs": outputs,
        "current_subtask_index": new_idx,
        "agent_sequence": seq,
    }


async def verifier_node(state: AgentState) -> Dict[str, Any]:
    task_id     = state["task_id"]
    prompt      = state["prompt"]
    retry_count = state.get("retry_count", 0)

    manager_agent.announce_start(task_id, "Verifier", "Final QA & Fact-Check")
    manager_agent.log_transition(task_id, "Executor", "Verifier", reason="all subtasks complete, running final QA")

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
                          f"Starting final verification and quality check (Attempt {retry_count + 1})...")

    result = await verifier_agent.verify_output(
        original_goal=prompt,
        generated_output=exec_content,
        task_id=task_id,
        subtask_id=None
    )

    # ── Self-healing retry loop ───────────────────────────────────────────
    if not result.is_valid and retry_count < 3:
        manager_agent.log_verifier_retry(
            task_id=task_id,
            attempt=retry_count + 1,
            max_retries=3,
            feedback=result.feedback,
        )

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

    # ── Task complete: Store memory reusing cached embedding ─────────────
    prompt_emb = state.get("prompt_embedding", None)
    memory_agent.store_memory(
        content=(
            f"Learned from goal '{prompt[:80]}...': "
            f"Verification Confidence Score: {result.confidence_score:.2f}. "
            f"Key observations: {result.feedback}"
        ),
        category="factual",
        embedding=prompt_emb,
    )

    status = "completed" if result.is_valid else "failed"
    update_task_in_db(task_id, status, final_result=result.verified_output)

    for sub in state["subtasks"]:
        if sub["assigned_agent"] == "verifier":
            update_subtask_in_db(sub["id"], status,
                                 output=result.verified_output,
                                 confidence_score=result.confidence_score)

    # ── Manager writes the final run summary ────────────────────────────
    seq = state.get("agent_sequence", []) + ["Verifier"]
    manager_agent.write_run_summary(
        task_id=task_id,
        verifier_retry_count=retry_count,
        final_confidence=result.confidence_score,
        status=status,
        agent_sequence=seq,
    )

    return {
        "verification_results": {
            "is_valid":         result.is_valid,
            "confidence_score": result.confidence_score,
            "feedback":         result.feedback
        },
        "verifier_feedback": "",
        "final_result":      result.verified_output,
        "agent_sequence":    seq,
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------
def route_subtasks(state: AgentState) -> Literal[
    "analyst", "executor", "memory_agent", "verifier", "__end__"
]:
    idx      = state["current_subtask_index"]
    subtasks = state["subtasks"]

    if idx >= len(subtasks):
        return "verifier"

    agent = subtasks[idx]["assigned_agent"]
    if agent == "analyst":
        return "analyst"
    elif agent == "executor":
        return "executor"
    elif agent == "memory_agent":
        return "memory_agent"
    elif agent == "verifier":
        return "verifier"
    return "executor"


def route_verifier_output(state: AgentState) -> Literal["executor", "__end__"]:
    v_res       = state.get("verification_results", {})
    retry_count = state.get("retry_count", 0)
    if v_res and not v_res.get("is_valid", True) and retry_count < 3:
        return "executor"
    return "__end__"


# ---------------------------------------------------------------------------
# Build and compile graph
# ---------------------------------------------------------------------------
builder = StateGraph(AgentState)

builder.add_node("planner",      planner_node)
builder.add_node("memory_agent",  memory_node)
builder.add_node("analyst",      analyst_node)
builder.add_node("executor",     executor_node)
builder.add_node("verifier",     verifier_node)

builder.set_entry_point("planner")

# Conditional edges after planner
builder.add_conditional_edges(
    "planner",
    route_subtasks,
    {
        "memory_agent": "memory_agent",
        "analyst":      "analyst",
        "executor":     "executor",
        "verifier":     "verifier",
    }
)

# Conditional edges after nodes
for node in ["memory_agent", "analyst", "executor"]:
    builder.add_conditional_edges(
        node,
        route_subtasks,
        {
            "memory_agent": "memory_agent",
            "analyst":      "analyst",
            "executor":     "executor",
            "verifier":     "verifier",
        }
    )

# Loopback or end
builder.add_conditional_edges(
    "verifier",
    route_verifier_output,
    {
        "executor": "executor",
        "__end__":  END,
    }
)

orchestrator_graph = builder.compile()
