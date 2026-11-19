import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.stream import token_stream_manager
from backend.app.core.idempotency import (
    validate_idempotency_key,
    compute_request_hash,
    compute_scope,
    clean_expired_keys
)
from backend.app.database.connection import get_db, SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog, IdempotencyKey
from backend.app.workflows.orchestrator import orchestrator_graph, run_task_pipeline
from backend.app.workflows.state import AgentState
from backend.app.workflows.gate_registry import gate_registry
from backend.app.workflows.task_registry import task_registry
from backend.app.harness.harness import get_harness_for_task

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

async def run_workflow_async(task_id: str, prompt: str, plugin_name: str) -> None:
    current_async_task = asyncio.current_task()
    if current_async_task:
        task_registry.register(task_id, current_async_task)
    try:
        await run_task_pipeline(task_id, prompt, plugin_name)
    except asyncio.CancelledError:
        logger.info(f"Task {task_id} execution cancelled.")
        raise
    except Exception as e:
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                task.final_result = f"Orchestrator error: {str(e)}"
                db.commit()
                
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
    finally:
        task_registry.unregister(task_id)

@router.post("")
async def create_task(
    payload: TaskCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    idempotency_key = request.headers.get("Idempotency-Key")
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
    scope = compute_scope(api_key)

    if not idempotency_key:
        if getattr(settings, "idempotency_required", False):
            raise HTTPException(status_code=422, detail="Idempotency-Key header is required.")

        task = Task(
            prompt=payload.prompt,
            plugin_name=payload.plugin_name,
            status="pending"
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        async_task = asyncio.create_task(run_workflow_async(task.id, task.prompt, task.plugin_name))
        task_registry.register(task.id, async_task)

        return JSONResponse(content=task.to_dict(), status_code=200)

    validate_idempotency_key(idempotency_key)
    clean_expired_keys(db)
    request_hash = compute_request_hash(payload.model_dump())

    now = datetime.utcnow()
    existing_key = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.scope == scope, IdempotencyKey.key == idempotency_key)
        .first()
    )

    if existing_key:
        if existing_key.expires_at >= now:
            if existing_key.request_hash == request_hash:
                task = db.query(Task).filter(Task.id == existing_key.task_id).first()
                if task:
                    return JSONResponse(
                        content=task.to_dict(),
                        status_code=existing_key.response_status or 200,
                        headers={"Idempotent-Replay": "true"}
                    )
            else:
                raise HTTPException(
                    status_code=422,
                    detail="Idempotency-Key already used with a different request payload."
                )
        else:
            db.delete(existing_key)
            db.commit()

    ttl_hours = getattr(settings, "idempotency_ttl_hours", 24)
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

    task = Task(
        prompt=payload.prompt,
        plugin_name=payload.plugin_name,
        status="pending"
    )

    try:
        db.add(task)
        db.flush()

        idem = IdempotencyKey(
            scope=scope,
            key=idempotency_key,
            request_hash=request_hash,
            task_id=task.id,
            response_status=200,
            expires_at=expires_at
        )
        db.add(idem)
        db.commit()
        db.refresh(task)
        is_creator = True
    except IntegrityError:
        db.rollback()
        is_creator = False
        winning_key = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.scope == scope, IdempotencyKey.key == idempotency_key)
            .first()
        )
        if winning_key and winning_key.request_hash == request_hash:
            winning_task = db.query(Task).filter(Task.id == winning_key.task_id).first()
            if winning_task:
                return JSONResponse(
                    content=winning_task.to_dict(),
                    status_code=winning_key.response_status or 200,
                    headers={"Idempotent-Replay": "true"}
                )
        raise HTTPException(
            status_code=422,
            detail="Idempotency-Key already used with a different request payload."
        )

    if is_creator:
        async_task = asyncio.create_task(run_workflow_async(task.id, task.prompt, task.plugin_name))
        task_registry.register(task.id, async_task)
        return JSONResponse(content=task.to_dict(), status_code=200)

@router.get("")
def list_tasks(
    skip: int = Query(0, ge=0, description="Number of tasks to skip for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of tasks to return"),
    db: Session = Depends(get_db)
):
    tasks = (
        db.query(Task)
        .order_by(Task.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
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
def approve_plan(task_id: str, payload: ApprovePlanPayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.subtasks is not None:
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

    log = AgentLog(
        task_id=task_id,
        agent_name="Manager",
        log_type="manager_decision",
        content="✅ [Manager] User approved execution plan. Resuming workforce execution..."
    )
    db.add(log)
    db.commit()

    gate_registry.signal(task_id)

    return {"message": "Plan approved successfully", "status": "running"}

@router.post("/{task_id}/steer")
def steer_task(task_id: str, payload: SteerPayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
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
        gate_registry.signal(task_id)
        return {"message": "Task completed by user override", "status": "completed"}

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

    gate_registry.signal(task_id)

    return {"message": "Steering feedback applied", "status": "running"}

@router.post("/{task_id}/reject")
def reject_task(task_id: str, payload: RejectPayload = RejectPayload(), db: Session = Depends(get_db)) -> Dict[str, Any]:
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

    task_registry.cancel(task_id)
    gate_registry.signal(task_id)

    return {"message": "Task cancelled", "status": "cancelled"}

@router.get("/{task_id}/logs")
def get_logs(task_id: str, db: Session = Depends(get_db)):
    logs = db.query(AgentLog).filter(AgentLog.task_id == task_id).order_by(AgentLog.id.asc()).all()
    return [l.to_dict() for l in logs]

# ── SSE DB Connection Pool Concurrency Limiter ─────────────────────────
# Binds the maximum number of concurrent DB sessions checked out by SSE streams.
# With PostgreSQL pool_size=5 (max_overflow=10), capping SSE stream DB access
# prevents long-lived event generators from starving REST endpoints or orchestrator writes.
_sse_db_semaphore: Optional[asyncio.Semaphore] = None

def get_sse_db_semaphore() -> asyncio.Semaphore:
    """Retrieve or initialize the global asyncio.Semaphore for SSE DB sessions."""
    global _sse_db_semaphore
    if _sse_db_semaphore is None:
        limit = getattr(settings, "sse_db_pool_limit", 5)
        _sse_db_semaphore = asyncio.Semaphore(limit)
    return _sse_db_semaphore

def set_sse_db_semaphore(sem: Optional[asyncio.Semaphore]) -> None:
    """Explicitly set or reset the SSE DB semaphore (useful for testing or config overrides)."""
    global _sse_db_semaphore
    _sse_db_semaphore = sem


@router.get("/{task_id}/stream")
async def stream_task_updates(task_id: str, request: Request = None):
    async def event_generator():
        import json
        last_log_id = 0
        last_status = None
        last_subtasks_status: Dict[str, str] = {}
        heartbeat_counter = 0          # fires a ping every ~15s (30 × 0.5s)
        sem = get_sse_db_semaphore()

        # Subscribe to live token stream
        token_queue = await token_stream_manager.subscribe(task_id)

        try:
            while True:
                # ── Disconnect check: terminate stream if client drops connection ──
                if request and await request.is_disconnected():
                    break

                # ── Drain any queued live token events immediately ─────────
                tokens_drained = 0
                while not token_queue.empty() and tokens_drained < 50:
                    try:
                        token_evt = token_queue.get_nowait()
                        tokens_drained += 1
                        yield f"data: {json.dumps(token_evt)}\n\n"
                    except asyncio.QueueEmpty:
                        break

                # ── Heartbeat: keep Render proxy from closing idle connections ──
                heartbeat_counter += 1
                if heartbeat_counter >= 30:
                    heartbeat_counter = 0
                    yield ": ping\n\n"      # SSE comment — ignored by browser, keeps TCP alive

                # ── Acquire bounded DB session pool semaphore ───────────────
                try:
                    async with asyncio.timeout(5.0):
                        async with sem:
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

                                    harness = get_harness_for_task(task_id)
                                    harness_data = harness.snapshot() if harness else None
                                    if not harness_data and task.failure_reason:
                                        try:
                                            parsed = json.loads(task.failure_reason)
                                            harness_data = parsed.get("harness")
                                        except Exception:
                                            pass

                                    payload = {
                                        "task_id":        task_id,
                                        "status":         task.status,
                                        "final_result":   task.final_result,
                                        "failure_reason": task.failure_reason,
                                        "subtasks":       subs_data,
                                        "new_logs":       [l.to_dict() for l in new_logs],
                                        "harness":        harness_data,
                                    }
                                    yield f"data: {json.dumps(payload)}\n\n"

                                    for l in new_logs:
                                        yield f"data: {json.dumps({'event': 'log', 'data': l.to_dict()})}\n\n"
                                    if status_changed:
                                        yield f"data: {json.dumps({'event': 'status_change', 'data': {'status': task.status}})}\n\n"

                                if task.status in ("completed", "failed", "cancelled"):
                                    harness = get_harness_for_task(task_id)
                                    harness_data = harness.snapshot() if harness else None
                                    if not harness_data and task.failure_reason:
                                        try:
                                            parsed = json.loads(task.failure_reason)
                                            harness_data = parsed.get("harness")
                                        except Exception:
                                            pass
                                    yield f"data: {json.dumps({'done': True, 'status': task.status, 'failure_reason': task.failure_reason, 'harness': harness_data})}\n\n"
                                    break

                            finally:
                                db.close()
                except (TimeoutError, asyncio.TimeoutError):
                    # DB pool limit reached; back off briefly and retry on next tick
                    yield f"data: {json.dumps({'warning': 'Database connection pool busy, retrying...'})}\n\n"
                    await asyncio.sleep(1.0)
                    continue
                except Exception as exc:
                    yield f"data: {json.dumps({'error': str(exc)})}\n\n"
                    break

                # ── Wait for next token or poll interval (0.3s) ───────────────
                try:
                    token_evt = await asyncio.wait_for(token_queue.get(), timeout=0.3)
                    yield f"data: {json.dumps(token_evt)}\n\n"
                except asyncio.TimeoutError:
                    pass
        finally:
            await token_stream_manager.unsubscribe(task_id, token_queue)

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

