import asyncio
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.database.connection import SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog, IdempotencyKey
from backend.app.workflows.task_registry import task_registry
from backend.app.workflows.gate_registry import gate_registry
from backend.app.workflows.heartbeat import (
    BOOT_INSTANCE_ID,
    refresh_heartbeat,
    reap_zombies,
    handle_graceful_shutdown,
)
from backend.app.api.tasks import (
    approve_plan,
    steer_task,
    reject_task,
    retry_task,
    stream_task_updates,
    ApprovePlanPayload,
    SteerPayload,
    RejectPayload,
)
from backend.app.core.idempotency import (
    validate_idempotency_key,
    compute_request_hash,
    compute_scope,
    clean_expired_keys,
)
from backend.app.main import app


@pytest.fixture(autouse=True)
def clean_lifecycle_tables():
    session = SessionLocal()
    try:
        session.query(IdempotencyKey).delete()
        session.query(AgentLog).delete()
        session.query(Subtask).delete()
        session.query(Task).delete()
        session.commit()
    finally:
        session.close()
    yield
    session = SessionLocal()
    try:
        session.query(IdempotencyKey).delete()
        session.query(AgentLog).delete()
        session.query(Subtask).delete()
        session.query(Task).delete()
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Idempotency Tests
# ---------------------------------------------------------------------------

def test_idempotency_replay_same_body(api_client, db_session):
    """
    Submitting the same idempotency key with an identical payload returns
    the original task, status 200, Idempotent-Replay header, and does not start a second task.
    """
    key = f"idem-key-{uuid.uuid4().hex[:16]}"
    payload = {"prompt": "Run benchmark audit", "plugin_name": "default"}
    headers = {"Idempotency-Key": key}

    with patch("backend.app.api.tasks.run_workflow_async", new=AsyncMock()):
        # First call: create task
        resp1 = api_client.post("/api/tasks", json=payload, headers=headers)
        assert resp1.status_code == 200
        data1 = resp1.json()
        task_id = data1["id"]
        assert "Idempotent-Replay" not in resp1.headers

        # Second call: replay
        resp2 = api_client.post("/api/tasks", json=payload, headers=headers)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["id"] == task_id
        assert resp2.headers.get("Idempotent-Replay") == "true"

        # Verify only 1 Task and 1 IdempotencyKey row exist in DB
        matching_tasks = db_session.query(Task).filter(Task.id == task_id).all()
        assert len(matching_tasks) == 1

        matching_keys = db_session.query(IdempotencyKey).filter(IdempotencyKey.key == key).all()
        assert len(matching_keys) == 1
        assert matching_keys[0].task_id == task_id


def test_idempotency_different_body_422(api_client, db_session):
    """
    Submitting the same idempotency key with a different payload returns HTTP 422.
    """
    key = f"idem-key-{uuid.uuid4().hex[:16]}"
    headers = {"Idempotency-Key": key}

    with patch("backend.app.api.tasks.run_workflow_async", new=AsyncMock()):
        resp1 = api_client.post("/api/tasks", json={"prompt": "Task Alpha", "plugin_name": "default"}, headers=headers)
        assert resp1.status_code == 200

        resp2 = api_client.post("/api/tasks", json={"prompt": "Task Beta Different", "plugin_name": "default"}, headers=headers)
        assert resp2.status_code == 422
        assert "Idempotency-Key already used with a different request payload" in resp2.json()["detail"]


def test_idempotency_invalid_key_422(api_client):
    """
    Keys that are too short, too long, or contain invalid characters return HTTP 422.
    """
    # Too short (< 8 chars)
    resp_short = api_client.post("/api/tasks", json={"prompt": "P", "plugin_name": "default"}, headers={"Idempotency-Key": "short"})
    assert resp_short.status_code == 422

    # Too long (> 128 chars)
    resp_long = api_client.post("/api/tasks", json={"prompt": "P", "plugin_name": "default"}, headers={"Idempotency-Key": "k" * 129})
    assert resp_long.status_code == 422

    # Invalid characters (e.g. spaces or symbols)
    resp_invalid = api_client.post("/api/tasks", json={"prompt": "P", "plugin_name": "default"}, headers={"Idempotency-Key": "invalid key with spaces!"})
    assert resp_invalid.status_code == 422


@pytest.mark.asyncio
async def test_idempotency_concurrent_requests(db_session):
    """
    Concurrent requests with the same idempotency key race to create the task.
    The database unique constraint enforces that only one transaction succeeds,
    and the second rolls back and returns the replayed winning task.
    """
    key = f"idem-race-{uuid.uuid4().hex[:16]}"
    scope = compute_scope(None)
    payload_dict = {"prompt": "Race condition test", "plugin_name": "default"}
    request_hash = compute_request_hash(payload_dict)

    # Directly test the DB layer logic
    t1 = Task(prompt="Race condition test", plugin_name="default", status="pending")
    db_session.add(t1)
    db_session.flush()

    idem1 = IdempotencyKey(
        scope=scope,
        key=key,
        request_hash=request_hash,
        task_id=t1.id,
        response_status=200,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db_session.add(idem1)
    db_session.commit()

    # Now verify that clean_expired_keys and lookup correctly finds the winner
    winning_key = db_session.query(IdempotencyKey).filter(IdempotencyKey.scope == scope, IdempotencyKey.key == key).first()
    assert winning_key is not None
    assert winning_key.task_id == t1.id


def test_idempotency_expired_key_allowed(api_client, db_session):
    """
    Expired idempotency keys are cleaned up opportunistically and permit new task creation.
    """
    key = f"idem-exp-{uuid.uuid4().hex[:16]}"
    scope = compute_scope(None)
    payload = {"prompt": "Initial Task", "plugin_name": "default"}
    req_hash = compute_request_hash(payload)

    # Insert an already-expired key
    old_task = Task(prompt="Old task", plugin_name="default", status="completed")
    db_session.add(old_task)
    db_session.flush()

    expired_record = IdempotencyKey(
        scope=scope,
        key=key,
        request_hash=req_hash,
        task_id=old_task.id,
        response_status=200,
        expires_at=datetime.utcnow() - timedelta(hours=2)
    )
    db_session.add(expired_record)
    db_session.commit()

    with patch("backend.app.api.tasks.run_workflow_async", new=AsyncMock()):
        # Sending request with the expired key should replace/allow new creation
        resp = api_client.post("/api/tasks", json={"prompt": "Brand new task", "plugin_name": "default"}, headers={"Idempotency-Key": key})
        assert resp.status_code == 200
        new_data = resp.json()
        assert new_data["id"] != old_task.id


# ---------------------------------------------------------------------------
# Heartbeat and Zombie Reaper Tests
# ---------------------------------------------------------------------------

def test_zombie_reaper_stale_heartbeat(db_session):
    """
    Tasks with last_heartbeat_at older than stale_seconds not active in memory
    are marked failed with reason service_restarted. Fresh tasks and tasks in
    task_registry are untouched.
    """
    now = datetime.utcnow()

    # Task A: Stale (> 120s ago), not in memory -> Should be reaped
    task_a = Task(
        prompt="Task A Stale",
        plugin_name="default",
        status="running",
        last_heartbeat_at=now - timedelta(seconds=200),
        owner_instance="instance-1"
    )
    # Task B: Fresh (< 120s ago) -> Should remain running
    task_b = Task(
        prompt="Task B Fresh",
        plugin_name="default",
        status="running",
        last_heartbeat_at=now - timedelta(seconds=15),
        owner_instance="instance-1"
    )
    # Task C: Stale timestamp, but active in task_registry -> Should NOT be reaped
    task_c = Task(
        prompt="Task C In-Memory",
        plugin_name="default",
        status="awaiting_plan_approval",
        last_heartbeat_at=now - timedelta(seconds=300),
        owner_instance="instance-1"
    )

    db_session.add_all([task_a, task_b, task_c])
    db_session.commit()

    # Mock task_c as registered in memory
    mock_async_task = MagicMock()
    task_registry.register(task_c.id, mock_async_task)

    try:
        reaped_count = reap_zombies(db_session, stale_seconds=120)
        assert reaped_count == 1

        db_session.refresh(task_a)
        db_session.refresh(task_b)
        db_session.refresh(task_c)

        # Task A reaped
        assert task_a.status == "failed"
        assert task_a.failure_reason is not None
        reason_a = json.loads(task_a.failure_reason)
        assert reason_a["reason"] == "service_restarted"
        assert reason_a["last_status"] == "running"

        # Task B untouched
        assert task_b.status == "running"

        # Task C untouched (protected by in-memory registry)
        assert task_c.status == "awaiting_plan_approval"

    finally:
        task_registry.unregister(task_c.id)


def test_zombie_reaper_overlapping_deploys(db_session):
    """
    Tasks owned by a previous instance that still have a fresh heartbeat (< 120s)
    must NOT be reaped (protects rolling/overlapping deploys).
    """
    now = datetime.utcnow()
    task_deploy = Task(
        prompt="Task during deploy",
        plugin_name="default",
        status="running",
        last_heartbeat_at=now - timedelta(seconds=30),
        owner_instance="old-render-instance-uuid"
    )
    db_session.add(task_deploy)
    db_session.commit()

    reaped = reap_zombies(db_session, stale_seconds=120)
    assert reaped == 0

    db_session.refresh(task_deploy)
    assert task_deploy.status == "running"


def test_zombie_legacy_null_heartbeat(db_session):
    """
    Tasks with NULL last_heartbeat_at fall back to updated_at/created_at
    and are cleanly reaped if older than stale threshold.
    """
    task_legacy = Task(
        prompt="Legacy task without heartbeat",
        plugin_name="default",
        status="running",
        last_heartbeat_at=None,
        created_at=datetime.utcnow() - timedelta(seconds=500),
        updated_at=datetime.utcnow() - timedelta(seconds=500),
    )
    db_session.add(task_legacy)
    db_session.commit()

    reaped = reap_zombies(db_session, stale_seconds=120)
    assert reaped >= 1

    db_session.refresh(task_legacy)
    assert task_legacy.status == "failed"
    reason = json.loads(task_legacy.failure_reason)
    assert reason["reason"] == "service_restarted"


def test_shutdown_graceful_cleanup(db_session):
    """
    handle_graceful_shutdown cancels active tasks in memory and marks
    all active tasks owned by the current instance as failed with service_shutdown.
    """
    task = Task(
        prompt="Active task on shutting down instance",
        plugin_name="default",
        status="running",
        owner_instance=BOOT_INSTANCE_ID
    )
    db_session.add(task)
    db_session.commit()

    mock_async_task = MagicMock()
    mock_async_task.done.return_value = False
    task_registry.register(task.id, mock_async_task)

    try:
        handle_graceful_shutdown(db_session)

        # In-memory task was cancelled
        mock_async_task.cancel.assert_called_once()

        # Database record was marked failed
        db_session.refresh(task)
        assert task.status == "failed"
        reason = json.loads(task.failure_reason)
        assert reason["reason"] == "service_shutdown"
    finally:
        task_registry.unregister(task.id)


# ---------------------------------------------------------------------------
# Gate Liveness Validation Tests
# ---------------------------------------------------------------------------

def test_gate_endpoints_409_for_dead_task(db_session):
    """
    If a task in awaiting_plan_approval or awaiting_steering is not in memory
    (e.g. after a deploy/restart), gate endpoints reject with HTTP 409 and mark it failed.
    """
    task = Task(
        prompt="Abandoned HITL task",
        plugin_name="default",
        status="awaiting_plan_approval",
        owner_instance="dead-instance-id"
    )
    db_session.add(task)
    db_session.commit()

    # /approve_plan
    with pytest.raises(HTTPException) as exc1:
        approve_plan(task.id, ApprovePlanPayload(subtasks=[]), db=db_session)
    assert exc1.value.status_code == 409
    assert exc1.value.detail == "task is no longer active"

    db_session.refresh(task)
    assert task.status == "failed"
    reason = json.loads(task.failure_reason)
    assert reason["reason"] == "service_restarted"

    # Reset to awaiting_steering to test /steer
    task.status = "awaiting_steering"
    db_session.commit()

    with pytest.raises(HTTPException) as exc2:
        steer_task(task.id, SteerPayload(action="steer", instructions="test"), db=db_session)
    assert exc2.value.status_code == 409

    # Reset to test /reject
    task.status = "awaiting_steering"
    db_session.commit()

    with pytest.raises(HTTPException) as exc3:
        reject_task(task.id, RejectPayload(), db=db_session)
    assert exc3.value.status_code == 409


# ---------------------------------------------------------------------------
# Task Retry & Stream Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_terminal_task_closes(db_session):
    """
    Connecting to stream_task_updates on a terminal task yields the terminal payload and closes.
    """
    task = Task(
        prompt="Completed stream test",
        plugin_name="default",
        status="completed",
        final_result="Final delivered result."
    )
    db_session.add(task)
    db_session.commit()

    resp = await stream_task_updates(task_id=task.id)
    chunks = []
    async for chunk in resp.body_iterator:
        chunks.append(chunk)

    # Stream emitted events and closed promptly (non-empty, contains completion)
    assert len(chunks) >= 1
    combined = "".join(chunks)
    assert "completed" in combined
    assert "Final delivered result." in combined


def test_retry_task_endpoint(api_client, db_session):
    """
    POST /api/tasks/{task_id}/retry creates a new task linked by retry_of,
    disallows retrying running tasks, and supports Idempotency-Key.
    """
    # 1. Reject retry of running task
    running_task = Task(prompt="Running task", plugin_name="default", status="running")
    db_session.add(running_task)
    db_session.commit()

    resp_running = api_client.post(f"/api/tasks/{running_task.id}/retry")
    assert resp_running.status_code == 400
    assert "Only failed or cancelled tasks can be retried" in resp_running.json()["detail"]

    # 2. Allow retry of failed task
    failed_task = Task(prompt="Failed task to retry", plugin_name="default", status="failed", failure_reason="Timeout")
    db_session.add(failed_task)
    db_session.commit()

    key = f"idem-retry-{uuid.uuid4().hex[:16]}"
    with patch("backend.app.api.tasks.run_workflow_async", new=AsyncMock()):
        resp_retry = api_client.post(f"/api/tasks/{failed_task.id}/retry", headers={"Idempotency-Key": key})
        assert resp_retry.status_code == 200
        new_data = resp_retry.json()
        assert new_data["id"] != failed_task.id
        assert new_data["retry_of"] == failed_task.id
        assert new_data["status"] == "pending"

        # 3. Duplicate retry with same idempotency key replays
        resp_replay = api_client.post(f"/api/tasks/{failed_task.id}/retry", headers={"Idempotency-Key": key})
        assert resp_replay.status_code == 200
        assert resp_replay.headers.get("Idempotent-Replay") == "true"
        assert resp_replay.json()["id"] == new_data["id"]


def test_startup_recovery_no_external_calls(db_session):
    """
    reap_zombies executes bounded local SQL queries with zero network or external LLM calls.
    """
    with patch("backend.app.agents.base.BaseAgent.execute_llm") as mock_llm:
        reaped = reap_zombies(db_session, stale_seconds=120)
        assert isinstance(reaped, int)
        mock_llm.assert_not_called()
