import logging
from typing import Dict, Any, List, Literal
from langgraph.graph import StateGraph, END

from backend.app.workflows.state import AgentState
from backend.app.agents.planner import PlannerAgent
from backend.app.agents.analyst_agent import AnalystAgent
from backend.app.agents.executor import ExecutorAgent
from backend.app.agents.verifier import VerifierAgent
from backend.app.agents.memory_agent import MemoryAgent

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


async def memory_node(state: AgentState) -> Dict[str, Any]:
    task_id    = state["task_id"]
    idx        = state["current_subtask_index"]
    subtask    = state["subtasks"][idx]
    subtask_id = subtask["id"]

    update_subtask_in_db(subtask_id, "running")

    # Call memory agent — it returns (output, prompt_embedding)
    output, query_vector = await memory_agent.run_subtask(
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
        "current_subtask_index": idx + 1,
        "prompt_embedding": query_vector  # Caches computed query embedding
    }


async def analyst_node(state: AgentState) -> Dict[str, Any]:
    task_id  = state["task_id"]
    idx      = state["current_subtask_index"]
    subtask  = state["subtasks"][idx]
    subtask_id = subtask["id"]

    update_subtask_in_db(subtask_id, "running")

    # Single-step Search + Reasoning
    output = await analyst_agent.run_subtask(
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

    # Gather prior context
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
        "current_subtask_index": new_idx
    }


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
                          f"Starting final verification and quality check (Attempt {retry_count + 1})...")
    
    result = await verifier_agent.verify_output(
        original_goal=prompt,
        generated_output=exec_content,
        task_id=task_id,
        subtask_id=None
    )

    # ── Self-healing retry loop (Verifier & QA) ──────────────────────────
    if not result.is_valid and retry_count < 3:
        msg = (
            f"🛡️ [QA/Verifier] Verification failed (score: {result.confidence_score:.2f}). "
            f"Feedback: {result.feedback}\n"
            f"Routing back to Executor (Attempt {retry_count + 1}/3)..."
        )
        verifier_agent.log_db(task_id, None, "thinking", msg)
        verifier_agent.log_db(task_id, None, "manager_decision", f"❌ QA GATE FAILED — Routing back to Executor for self-healing: {result.feedback}")
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

    # ── Task complete: Store memory reusing cached embedding ─────────────
    prompt_emb = state.get("prompt_embedding", None)
    memory_agent.store_memory(
        content=(
            f"Learned from goal '{prompt[:80]}...': "
            f"Verification Confidence Score: {result.confidence_score:.2f}. "
            f"Key observations: {result.feedback}"
        ),
        category="factual",
        embedding=prompt_emb  # Bypasses LLM call to save token budget & latency
    )

    status = "completed" if result.is_valid else "failed"
    update_task_in_db(task_id, status, final_result=result.verified_output)

    for sub in state["subtasks"]:
        if sub["assigned_agent"] == "verifier":
            update_subtask_in_db(sub["id"], status,
                                 output=result.verified_output,
                                 confidence_score=result.confidence_score)

    # ── Write run summary for frontend terminal ─────────────────────────
    summary_markdown = (
        f"# 📋 Agentic Workforce Run Summary\n\n"
        f"**Final Status:** `{status.upper()}`  \n"
        f"**QA Verification Certainty:** `{result.confidence_score:.0%}`  \n"
        f"**Self-Healing Retries executed:** `{retry_count}`  \n\n"
        f"**Latency Optimization Metrics:**\n"
        f"- Target API Calls: **5**\n"
        f"- Memory Embedding: **Cached & Reused** (0 extra embedding calls during storage)\n"
        f"- Analyst Node: **Search & Reasoning combined** (saved 1 reasoning text call)\n"
    )
    verifier_agent.log_db(task_id, None, "manager_decision", summary_markdown)

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
