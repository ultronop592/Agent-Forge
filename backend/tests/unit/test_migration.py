import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.models import Base, Task, Memory, AgentLog, MCPServer
from backend.app.database.connection import get_database_status
from backend.scripts.migrate_to_postgres import get_engine_for_url, migrate_data


def test_url_normalization():
    eng = get_engine_for_url("postgres://user:pass@localhost:5432/mydb")
    assert str(eng.url).startswith("postgresql://")


def test_get_database_status():
    status = get_database_status()
    assert "status" in status
    assert "dialect" in status
    assert status["status"] in ("connected", "disconnected")


def test_migrate_data_end_to_end(tmp_path):
    src_file = tmp_path / "source.db"
    tgt_file = tmp_path / "target.db"

    src_url = f"sqlite:///{src_file}"
    tgt_url = f"sqlite:///{tgt_file}"

    src_engine = create_engine(src_url)
    Base.metadata.create_all(bind=src_engine)

    Session = sessionmaker(bind=src_engine)
    db = Session()
    try:
        # Seed test data in source
        task = Task(id="test-task-1", prompt="Analyze market", plugin_name="business")
        db.add(task)
        mem = Memory(id="test-mem-1", category="factual", content="Important knowledge", embedding=[0.1]*768)
        db.add(mem)
        log = AgentLog(task_id="test-task-1", agent_name="Planner", log_type="thinking", content="Planning step")
        db.add(log)
        mcp = MCPServer(id="test-mcp-1", name="filesystem", command="npx", args="[]")
        db.add(mcp)
        db.commit()
    finally:
        db.close()

    # Run migration
    success = migrate_data(src_url, tgt_url)
    assert success is True

    # Verify target contents
    tgt_engine = create_engine(tgt_url)
    TgtSession = sessionmaker(bind=tgt_engine)
    tgt_db = TgtSession()
    try:
        t = tgt_db.query(Task).filter(Task.id == "test-task-1").first()
        assert t is not None
        assert t.prompt == "Analyze market"

        m = tgt_db.query(Memory).filter(Memory.id == "test-mem-1").first()
        assert m is not None
        assert m.content == "Important knowledge"

        l = tgt_db.query(AgentLog).filter(AgentLog.task_id == "test-task-1").first()
        assert l is not None
        assert l.agent_name == "Planner"

        s = tgt_db.query(MCPServer).filter(MCPServer.id == "test-mcp-1").first()
        assert s is not None
        assert s.name == "filesystem"
    finally:
        tgt_db.close()

    # Re-running migration should skip duplicates without error
    success_rerun = migrate_data(src_url, tgt_url)
    assert success_rerun is True
