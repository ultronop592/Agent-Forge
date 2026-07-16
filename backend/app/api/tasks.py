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

@router.get("/{task_id}/logs")
def get_logs(task_id: str, db: Session = Depends(get_db)):
    logs = db.query(AgentLog).filter(AgentLog.task_id == task_id).order_by(AgentLog.id.asc()).all()
    return [l.to_dict() for l in logs]

@router.get("/{task_id}/stream")
async def stream_task_updates(task_id: str):
    async def event_generator():
        last_log_id = 0
        last_status = None
        last_subtasks_status = {}
        
        while True:
            db = SessionLocal()
            try:
                task = db.query(Task).filter(Task.id == task_id).first()
                if not task:
                    yield f"data: {{\"error\": \"Task not found\"}}\n\n"
                    break
                
                # Check for status change
                status_changed = False
                if task.status != last_status:
                    last_status = task.status
                    status_changed = True
                
                # Check for subtasks updates
                subtasks = db.query(Subtask).filter(Subtask.task_id == task_id).order_by(Subtask.order_index.asc()).all()
                subs_updated = False
                subs_data = []
                for s in subtasks:
                    subs_data.append(s.to_dict())
                    if last_subtasks_status.get(s.id) != s.status:
                        last_subtasks_status[s.id] = s.status
                        subs_updated = True
                
                # Fetch new logs
                new_logs = db.query(AgentLog).filter(AgentLog.task_id == task_id, AgentLog.id > last_log_id).order_by(AgentLog.id.asc()).all()
                
                if new_logs or status_changed or subs_updated:
                    if new_logs:
                        last_log_id = new_logs[-1].id
                    
                    update_payload = {
                        "task_id": task_id,
                        "status": task.status,
                        "final_result": task.final_result,
                        "subtasks": subs_data,
                        "new_logs": [l.to_dict() for l in new_logs]
                    }
                    
                    yield f"data: {json.dumps(update_payload)}\n\n"
                
                # Stop streaming if execution is finalized
                if task.status in ["completed", "failed"]:
                    break
            except Exception as e:
                yield f"data: {{\"error\": \"Stream error: {str(e)}\"}}\n\n"
                break
            finally:
                db.close()
                
            await asyncio.sleep(0.5) # Poll interval
            
    import json
    return StreamingResponse(event_generator(), media_type="text/event-stream")
