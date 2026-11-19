import time
import json
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.database.connection import SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog
from backend.app.workflows.task_registry import task_registry

logger = logging.getLogger("agentforge.workflows.heartbeat")

BOOT_INSTANCE_ID = str(uuid.uuid4())

_last_heartbeat_sent: Dict[str, float] = {}


def refresh_heartbeat(task_id: str, throttle_seconds: float = 15.0) -> None:
    now_mono = time.monotonic()
    last_sent = _last_heartbeat_sent.get(task_id, 0.0)
    if now_mono - last_sent < throttle_seconds:
        return

    _last_heartbeat_sent[task_id] = now_mono
    db = SessionLocal()
    try:
        db.query(Task).filter(Task.id == task_id).update({
            Task.last_heartbeat_at: datetime.utcnow(),
            Task.owner_instance: BOOT_INSTANCE_ID
        })
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to refresh heartbeat for task {task_id}: {e}")
    finally:
        db.close()


def reap_zombies(session: Session, stale_seconds: int = 120) -> int:
    cutoff = datetime.utcnow() - timedelta(seconds=stale_seconds)
    non_terminal = ["pending", "running", "awaiting_plan_approval", "awaiting_steering"]

    last_active = func.coalesce(Task.last_heartbeat_at, Task.updated_at, Task.created_at)
    query = session.query(Task).filter(
        Task.status.in_(non_terminal),
        last_active < cutoff
    )

    active_ids = list(task_registry._tasks.keys())
    if active_ids:
        query = query.filter(~Task.id.in_(active_ids))

    zombies = query.all()
    if not zombies:
        return 0

    reaped_count = 0
    for z in zombies:
        last_sub = (
            session.query(Subtask)
            .filter(Subtask.task_id == z.id, Subtask.status == "completed")
            .order_by(Subtask.order_index.desc())
            .first()
        )
        subtask_name = last_sub.title if last_sub else None

        reason_payload = json.dumps({
            "reason": "service_restarted",
            "last_status": z.status,
            "last_completed_subtask": subtask_name
        })

        z.status = "failed"
        z.failure_reason = reason_payload

        log = AgentLog(
            task_id=z.id,
            agent_name="Manager",
            log_type="manager_decision",
            content="⚠️ [Manager] Task was abandoned due to service restart or instance spin-down. Marked as failed."
        )
        session.add(log)
        reaped_count += 1

    try:
        session.commit()
        logger.info(f"Reaped {reaped_count} zombie task(s) abandoned across restarts.")
    except Exception as e:
        logger.error(f"Failed to commit zombie task reap: {e}")
        session.rollback()

    return reaped_count


async def reaper_background_loop() -> None:
    logger.info("Starting background zombie task reaper loop.")
    while True:
        try:
            interval = getattr(settings, "task_reaper_interval_seconds", 60)
            await asyncio.sleep(interval)
            db = SessionLocal()
            try:
                stale_sec = getattr(settings, "task_stale_seconds", 120)
                reap_zombies(db, stale_sec)
            finally:
                db.close()
        except asyncio.CancelledError:
            logger.info("Zombie task reaper loop cancelled.")
            break
        except Exception as e:
            logger.warning(f"Error in zombie reaper background loop: {e}")


def handle_graceful_shutdown(session: Session) -> None:
    logger.info("Executing graceful shutdown for in-flight tasks.")
    for tid in list(task_registry._tasks.keys()):
        try:
            task_registry.cancel(tid)
        except Exception:
            pass

    try:
        non_terminal = ["pending", "running", "awaiting_plan_approval", "awaiting_steering"]
        tasks = session.query(Task).filter(
            Task.owner_instance == BOOT_INSTANCE_ID,
            Task.status.in_(non_terminal)
        ).all()

        for t in tasks:
            t.status = "failed"
            t.failure_reason = json.dumps({"reason": "service_shutdown"})
            log = AgentLog(
                task_id=t.id,
                agent_name="Manager",
                log_type="manager_decision",
                content="⚠️ [Manager] Task was terminated due to server shutdown."
            )
            session.add(log)

        session.commit()
        logger.info(f"Marked {len(tasks)} local active task(s) as failed on shutdown.")
    except Exception as e:
        logger.warning(f"Non-fatal error updating tasks during shutdown: {e}")
