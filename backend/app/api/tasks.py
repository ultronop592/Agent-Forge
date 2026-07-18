import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from backend.app.database.connection import get_db, SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog
from backend.app.workflows.orchestrator import orchestrator_graph
from backend.app.workflows.state import AgentState

router = APIRouter(prefix="/tasks", tags=["tasks"])

class TaskCreate(BaseModel):
    prompt: str
    plugin_name: str

class SubtaskUpdate(BaseModel):
    id: str | None = None
    title: str
    description: str = ""
    assigned_agent: str = "analyst"

class ApprovePlanPayload(BaseModel):
    subtasks: List[SubtaskUpdate] | None = None

class SteerPayload(BaseModel):
    steering_prompt: str = ""
    action: str = "steer"  # "steer" | "force_complete"

class RejectPayload(BaseModel):
    reason: str = ""

async def run_workflow_async(task_id: str, prompt: str, plugin_name: str):
    try:
        initial_state: AgentState = {
            "task_id": task_id,
            "prompt": prompt,
            "plugin_name": plugin_name,
            "subtasks": [],
            "current_subtask_index": 0,
            "agent_outputs": {},
            "verification_results": {},
            "final_result": "",
            "retry_count": 0,
            "verifier_feedback": "",
            "prompt_embedding": [],
            "agent_sequence": [],           # Manager populates this as agents run
            # ── Manager Agent tracking ────────────────────────────────
            "manager_quality_scores": {},
            "manager_skip_flags": {},
            "agent_retry_counts": {},
        }
        
        # Invoke the compiled LangGraph flow
        await orchestrator_graph.ainvoke(initial_state)
    except Exception as e:
        # Mark task as failed in case of unhandled errors
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                task.final_result = f"Orchestrator error: {str(e)}"
                db.commit()
                
                # Write an error log
                error_log = AgentLog(
                    task_id=task_id,
                    agent_name="System",
                    log_type="error",
                    content=f"Workflow execution failed: {str(e)}"
                )
                db.add(error_log)
                db.commit()
        finally:
            db.close()

@router.post("")
async def create_task(payload: TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    task = Task(
        prompt=payload.prompt,
        plugin_name=payload.plugin_name,
        status="pending"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Run the orchestrator in the background
    background_tasks.add_task(run_workflow_async, task.id, task.prompt, task.plugin_name)
    
    return task.to_dict()

@router.get("")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return [t.to_dict() for t in tasks]

@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    subtasks = db.query(Subtask).filter(Subtask.task_id == task_id).order_by(Subtask.order_index.asc()).all()
    
    res = task.to_dict()
    res["subtasks"] = [s.to_dict() for s in subtasks]
    return res

@router.delete("/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted successfully"}

@router.post("/{task_id}/approve_plan")
def approve_plan(task_id: str, payload: ApprovePlanPayload, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.subtasks is not None:
        # User customized the subtasks list: delete existing and replace with modified list
        db.query(Subtask).filter(Subtask.task_id == task_id).delete()
        db.commit()

        for idx, sub in enumerate(payload.subtasks):
            new_sub = Subtask(
                task_id=task_id,
                title=sub.title,
                description=sub.description,
                assigned_agent=sub.assigned_agent,
                status="pending",
                order_index=idx
            )
            db.add(new_sub)
        db.commit()

    task.status = "running"
    db.commit()

    # Log Manager approval action
    log = AgentLog(
        task_id=task_id,
        agent_name="Manager",
        log_type="manager_decision",
        content="✅ [Manager] User approved execution plan. Resuming workforce execution..."
    )
    db.add(log)
    db.commit()

    return {"message": "Plan approved successfully", "status": "running"}

@router.post("/{task_id}/steer")
def steer_task(task_id: str, payload: SteerPayload, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.action == "force_complete":
        task.status = "completed"
        db.commit()
        log = AgentLog(
            task_id=task_id,
            agent_name="Manager",
            log_type="manager_decision",
            content="✅ [Manager] User accepted current deliverable and forced completion."
        )
        db.add(log)
        db.commit()
        return {"message": "Task completed by user override", "status": "completed"}

    # Action is steer: record steering prompt and resume running
    task.status = "running"
    db.commit()

    steer_log = AgentLog(
        task_id=task_id,
        agent_name="User",
        log_type="steering",
        content=payload.steering_prompt
    )
    manager_log = AgentLog(
        task_id=task_id,
        agent_name="Manager",
        log_type="manager_decision",
        content=f"🔄 [Manager] User steering feedback received: '{payload.steering_prompt}'. Resuming execution..."
    )
    db.add(steer_log)
    db.add(manager_log)
    db.commit()

    return {"message": "Steering feedback applied", "status": "running"}

@router.post("/{task_id}/reject")
def reject_task(task_id: str, payload: RejectPayload = RejectPayload(), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "cancelled"
    db.commit()

    log = AgentLog(
        task_id=task_id,
        agent_name="Manager",
        log_type="manager_decision",
        content=f"❌ [Manager] Task execution cancelled by user. {payload.reason}".strip()
    )
    db.add(log)
    db.commit()

    return {"message": "Task cancelled", "status": "cancelled"}

@router.get("/{task_id}/logs")
def get_logs(task_id: str, db: Session = Depends(get_db)):
    logs = db.query(AgentLog).filter(AgentLog.task_id == task_id).order_by(AgentLog.id.asc()).all()
    return [l.to_dict() for l in logs]

@router.get("/{task_id}/stream")
async def stream_task_updates(task_id: str):
    async def event_generator():
        import json
        last_log_id = 0
        last_status = None
        last_subtasks_status: Dict[str, str] = {}
        heartbeat_counter = 0          # fires a ping every ~15s (30 × 0.5s)

        while True:
            # ── Heartbeat: keep Render proxy from closing idle connections ──
            heartbeat_counter += 1
            if heartbeat_counter >= 30:
                heartbeat_counter = 0
                yield ": ping\n\n"      # SSE comment — ignored by browser, keeps TCP alive

            db = SessionLocal()
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if not task:
                    yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                    break

                # ── Status change detection ──────────────────────────────
                status_changed = task.status != last_status
                if status_changed:
                    last_status = task.status

                # ── Subtask change detection ─────────────────────────────
                subtasks = (
                    db.query(Subtask)
                    .filter(Subtask.task_id == task_id)
                    .order_by(Subtask.order_index.asc())
                    .all()
                )
                subs_updated = False
                subs_data = []
                for s in subtasks:
                    subs_data.append(s.to_dict())
                    if last_subtasks_status.get(s.id) != s.status:
                        last_subtasks_status[s.id] = s.status
                        subs_updated = True

                # ── New log lines since last poll ────────────────────────
                new_logs = (
                    db.query(AgentLog)
                    .filter(AgentLog.task_id == task_id, AgentLog.id > last_log_id)
                    .order_by(AgentLog.id.asc())
                    .all()
                )

                if new_logs or status_changed or subs_updated:
                    if new_logs:
                        last_log_id = new_logs[-1].id

                    payload = {
                        "task_id":      task_id,
                        "status":       task.status,
                        "final_result": task.final_result,
                        "subtasks":     subs_data,
                        "new_logs":     [l.to_dict() for l in new_logs],
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                # ── Terminal condition ───────────────────────────────────
                if task.status in ("completed", "failed", "cancelled"):
                    # Send one final done event so the client knows cleanly
                    yield f"data: {json.dumps({'done': True, 'status': task.status})}\n\n"
                    break

            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"
                break
            finally:
                db.close()

            await asyncio.sleep(0.5)   # 500 ms poll interval

    # ── Production-safe SSE response headers ────────────────────────────────
    # Cache-Control + X-Accel-Buffering prevent nginx/CDN from buffering the stream.
    headers = {
        "Cache-Control":      "no-cache",
        "X-Accel-Buffering":  "no",       # nginx directive — disables proxy buffering
        "Connection":         "keep-alive",
        "Content-Type":       "text/event-stream",
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )
