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

from backend.app.database.connection import SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog

logger = logging.getLogger("agentforge.workflows")

# Instantiate agents
planner_agent = PlannerAgent()
researcher_agent = ResearcherAgent()
reasoner_agent = ReasonerAgent()
executor_agent = ExecutorAgent()
verifier_agent = VerifierAgent()
memory_agent = MemoryAgent()

# Helper to update subtask status in DB
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

# Helper to update task status in DB
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

# Nodes implementations
async def planner_node(state: AgentState) -> Dict[str, Any]:
    task_id = state["task_id"]
    prompt = state["prompt"]
    
    update_task_in_db(task_id, "running")
    
    # Generate subtasks using LLM
    plan = await planner_agent.create_plan(prompt, task_id)
    
    # Save subtasks to DB
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
    task_id = state["task_id"]
    idx = state["current_subtask_index"]
    subtask = state["subtasks"][idx]
    subtask_id = subtask["id"]
    
    update_subtask_in_db(subtask_id, "running")
    
    # Run the researcher subtask
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
        "current_subtask_index": idx + 1
    }

async def reasoner_node(state: AgentState) -> Dict[str, Any]:
    task_id = state["task_id"]
    idx = state["current_subtask_index"]
    subtask = state["subtasks"][idx]
    subtask_id = subtask["id"]
    
    update_subtask_in_db(subtask_id, "running")
    
    # Gather previous subtasks outputs as context
    prev_context = "\n\n".join([f"--- Subtask: {sub['title']} ---\n{output}" for sub_id, output in state["agent_outputs"].items() for sub in state["subtasks"] if sub["id"] == sub_id])
    
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
        "current_subtask_index": idx + 1
    }

async def executor_node(state: AgentState) -> Dict[str, Any]:
    task_id = state["task_id"]
    idx = state["current_subtask_index"]
    subtask = state["subtasks"][idx]
    subtask_id = subtask["id"]
    
    update_subtask_in_db(subtask_id, "running")
    
    # Gather previous context
    context = "\n\n".join([f"--- Context: {sub['title']} ---\n{output}" for sub_id, output in state["agent_outputs"].items() for sub in state["subtasks"] if sub["id"] == sub_id])
    
    output = await executor_agent.run_subtask(
        subtask_title=subtask["title"],
        subtask_desc=subtask["description"],
        context=context,
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

async def memory_node(state: AgentState) -> Dict[str, Any]:
    task_id = state["task_id"]
    idx = state["current_subtask_index"]
    subtask = state["subtasks"][idx]
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

async def verifier_node(state: AgentState) -> Dict[str, Any]:
    task_id = state["task_id"]
    prompt = state["prompt"]
    
    # Gather final output from the Executor subtask(s)
    executor_outputs = []
    for sub in state["subtasks"]:
        sub_id = sub["id"]
        if sub["assigned_agent"] == "executor" and sub_id in state["agent_outputs"]:
            executor_outputs.append(state["agent_outputs"][sub_id])
            
    exec_content = "\n\n".join(executor_outputs) if executor_outputs else "\n\n".join(state["agent_outputs"].values())
    
    # Run verification
    # We will log verification on the task level (subtask_id=None or create a verification log entry)
    verifier_agent.log_db(task_id, None, "thinking", "Starting final verification checks...")
    result = await verifier_agent.verify_output(
        original_goal=prompt,
        generated_output=exec_content,
        task_id=task_id,
        subtask_id=None
    )
    
    # Save the resulting memory learning
    memory_agent.store_memory(
        content=f"Learned from goal '{prompt[:80]}...': Verification Confidence Score: {result.confidence_score:.2f}. Key observations: {result.feedback}",
        category="factual"
    )
    
    update_task_in_db(task_id, "completed", final_result=result.verified_output)
    
    # Update the verifier subtask in database if one exists
    for sub in state["subtasks"]:
        if sub["assigned_agent"] == "verifier":
            update_subtask_in_db(sub["id"], "completed", output=result.verified_output, confidence_score=result.confidence_score)
            
    return {
        "verification_results": {
            "is_valid": result.is_valid,
            "confidence_score": result.confidence_score,
            "feedback": result.feedback
        },
        "final_result": result.verified_output
    }

# Conditional routing edge
def route_subtasks(state: AgentState) -> Literal["researcher", "reasoner", "executor", "memory_agent", "verifier", "__end__"]:
    idx = state["current_subtask_index"]
    subtasks = state["subtasks"]
    
    if idx >= len(subtasks):
        return "verifier"
        
    next_subtask = subtasks[idx]
    agent = next_subtask["assigned_agent"]
    
    if agent == "researcher":
        return "researcher"
    elif agent == "reasoner":
        return "reasoner"
    elif agent == "executor":
        return "executor"
    elif agent == "memory_agent":
        return "memory_agent"
    elif agent == "verifier":
        # If the planner explicitly generated a verifier task, route to verifier.
        return "verifier"
    else:
        # Fallback to executor
        return "executor"

# Build and compile graph
builder = StateGraph(AgentState)

builder.add_node("planner", planner_node)
builder.add_node("researcher", researcher_node)
builder.add_node("reasoner", reasoner_node)
builder.add_node("executor", executor_node)
builder.add_node("memory_agent", memory_node)
builder.add_node("verifier", verifier_node)

builder.set_entry_point("planner")

builder.add_conditional_edges(
    "planner",
    route_subtasks,
    {
        "researcher": "researcher",
        "reasoner": "reasoner",
        "executor": "executor",
        "memory_agent": "memory_agent",
        "verifier": "verifier"
    }
)

for node in ["researcher", "reasoner", "executor", "memory_agent"]:
    builder.add_conditional_edges(
        node,
        route_subtasks,
        {
            "researcher": "researcher",
            "reasoner": "reasoner",
            "executor": "executor",
            "memory_agent": "memory_agent",
            "verifier": "verifier"
        }
    )

builder.add_edge("verifier", END)

orchestrator_graph = builder.compile()
