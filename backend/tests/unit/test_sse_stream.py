import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.api.tasks import (
    stream_task_updates,
    get_sse_db_semaphore,
    set_sse_db_semaphore,
)
from backend.app.core.config import settings
from backend.app.database.connection import SessionLocal
from backend.app.database.models import Task, Subtask, AgentLog


@pytest.fixture(autouse=True)
def reset_semaphore():
    """Reset the global SSE DB semaphore before and after each test."""
    set_sse_db_semaphore(None)
    yield
    set_sse_db_semaphore(None)


def test_get_and_set_sse_db_semaphore():
    """Verify semaphore initializes with configured limit and can be overridden."""
    sem = get_sse_db_semaphore()
    assert isinstance(sem, asyncio.Semaphore)
    assert sem._value == settings.sse_db_pool_limit

    custom_sem = asyncio.Semaphore(2)
    set_sse_db_semaphore(custom_sem)
    assert get_sse_db_semaphore() is custom_sem
    assert get_sse_db_semaphore()._value == 2


@pytest.mark.asyncio
async def test_sse_stream_completes_and_releases_semaphore():
    """
    Verify stream_task_updates yields task data and properly releases
    the semaphore permit back to full capacity on stream completion.
    """
    db = SessionLocal()
    task = Task(prompt="Test SSE stream task", plugin_name="default", status="completed", final_result="All good.")
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id
    db.close()

    try:
        custom_sem = asyncio.Semaphore(3)
        set_sse_db_semaphore(custom_sem)

        resp = await stream_task_updates(task_id=task_id)
        events = []

        # Read all events from the stream
        async for chunk in resp.body_iterator:
            events.append(chunk)

        full_stream = "".join(events)
        assert "All good." in full_stream or "completed" in full_stream
        assert "done" in full_stream

        # Verify semaphore capacity is completely restored
        assert custom_sem._value == 3
    finally:
        db = SessionLocal()
        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            db.delete(t)
            db.commit()
        db.close()


@pytest.mark.asyncio
async def test_sse_stream_task_not_found_releases_semaphore():
    """
    Verify stream_task_updates handles nonexistent task by yielding
    error event and immediately restoring semaphore capacity.
    """
    custom_sem = asyncio.Semaphore(2)
    set_sse_db_semaphore(custom_sem)

    resp = await stream_task_updates(task_id="nonexistent-task-id-999")
    events = []
    async for chunk in resp.body_iterator:
        events.append(chunk)

    full_stream = "".join(events)
    assert "Task not found" in full_stream
    assert custom_sem._value == 2


@pytest.mark.asyncio
async def test_sse_stream_client_disconnect_terminates_loop():
    """
    Verify that when the client disconnects (request.is_disconnected returns True),
    the event generator terminates and releases the semaphore.
    """
    db = SessionLocal()
    task = Task(prompt="Test disconnect task", plugin_name="default", status="running")
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id
    db.close()

    try:
        custom_sem = asyncio.Semaphore(1)
        set_sse_db_semaphore(custom_sem)

        # Mock Request where is_disconnected returns False initially then True
        mock_request = MagicMock()
        disconnect_calls = 0

        async def mock_is_disconnected():
            nonlocal disconnect_calls
            disconnect_calls += 1
            # Disconnect on second check
            return disconnect_calls >= 2

        mock_request.is_disconnected = mock_is_disconnected

        resp = await stream_task_updates(task_id=task_id, request=mock_request)
        events = []
        async for chunk in resp.body_iterator:
            events.append(chunk)

        # Loop must terminate after disconnect
        assert disconnect_calls >= 2
        assert custom_sem._value == 1
    finally:
        db = SessionLocal()
        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            db.delete(t)
            db.commit()
        db.close()


@pytest.mark.asyncio
async def test_sse_stream_db_busy_timeout():
    """
    Verify that when the semaphore cannot be acquired within the timeout
    (e.g., all DB sessions in pool are saturated), the generator yields
    a 'Database connection pool busy' warning and retries without crashing.
    """
    from unittest.mock import patch

    mock_request = MagicMock()
    disconnect_calls = 0

    async def mock_is_disconnected():
        nonlocal disconnect_calls
        disconnect_calls += 1
        return disconnect_calls >= 2

    mock_request.is_disconnected = mock_is_disconnected

    with patch("asyncio.timeout", side_effect=TimeoutError("Pool saturated")):
        resp = await stream_task_updates(task_id="any-task", request=mock_request)
        events = []
        async for chunk in resp.body_iterator:
            events.append(chunk)

    full_stream = "".join(events)
    assert "Database connection pool busy" in full_stream


@pytest.mark.asyncio
async def test_sse_stream_receives_live_token_chunks():
    """
    Verify that tokens published to TokenStreamManager are received in
    real-time through the SSE stream.
    """
    from backend.app.core.stream import token_stream_manager
    task_id = "test-live-stream-task-123"

    db = SessionLocal()
    task = Task(id=task_id, prompt="Test stream prompt", plugin_name="default", status="running")
    db.add(task)
    db.commit()
    db.close()

    try:
        mock_request = MagicMock()
        disconnect_calls = 0

        async def mock_is_disconnected():
            nonlocal disconnect_calls
            disconnect_calls += 1
            return disconnect_calls >= 3

        mock_request.is_disconnected = mock_is_disconnected

        # Publish live token chunks in the background
        async def publish_tokens():
            await asyncio.sleep(0.05)
            await token_stream_manager.publish_token(
                task_id=task_id,
                agent_name="Coder",
                chunk="def stream_code():\n",
                subtask_id="sub-1"
            )
            await token_stream_manager.publish_token(
                task_id=task_id,
                agent_name="Coder",
                chunk="    return True\n",
                subtask_id="sub-1"
            )

        asyncio.create_task(publish_tokens())

        resp = await stream_task_updates(task_id=task_id, request=mock_request)
        events = []
        async for chunk in resp.body_iterator:
            events.append(chunk)

        full_stream = "".join(events)
        assert "def stream_code():" in full_stream
        assert "return True" in full_stream
        assert '"event": "token"' in full_stream
    finally:
        db = SessionLocal()
        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            db.delete(t)
            db.commit()
        db.close()



@pytest.mark.asyncio
async def test_base_agent_execute_llm_streams_tokens():
    """
    Verify that BaseAgent.execute_llm streams tokens to TokenStreamManager.
    """
    from backend.app.agents.base import BaseAgent
    from backend.app.core.stream import token_stream_manager

    task_id = "test-agent-stream-task-456"
    sub_q = await token_stream_manager.subscribe(task_id)

    try:
        agent = BaseAgent(name="TestStreamer", system_instruction="Streaming tester")
        agent.has_llm = False  # Demo streaming mode

        output = await agent.execute_llm(
            prompt="Stream test prompt",
            task_id=task_id,
            mock_response_content="TokenA TokenB TokenC"
        )

        assert output == "TokenA TokenB TokenC"

        received_chunks = []
        while not sub_q.empty():
            evt = sub_q.get_nowait()
            received_chunks.append(evt["data"]["chunk"])

        combined = "".join(received_chunks)
        assert "TokenA" in combined
        assert "TokenB" in combined
        assert "TokenC" in combined
    finally:
        await token_stream_manager.unsubscribe(task_id, sub_q)
