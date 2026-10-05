#!/usr/bin/env python3
"""
AgentForge SQLite to PostgreSQL Migration Utility.

Usage:
    python -m backend.scripts.migrate_to_postgres \
        --source sqlite:///./agentforge.db \
        --target postgresql://agentforge:agentforge_password@localhost:5432/agentforge

Or set the TARGET via environment variable:
    export DATABASE_URL=postgresql://user:pass@localhost:5432/agentforge
    python -m backend.scripts.migrate_to_postgres
"""

import sys
import os
import argparse
import logging
from typing import Dict, Any

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.database.models import Base, Task, Subtask, AgentLog, Memory, MCPServer
from backend.app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("db_migration")


def get_engine_for_url(url: str):
    """Creates an engine with proper parameters depending on dialect."""
    # Normalize postgres:// to postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    connect_args = {}
    engine_kwargs = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10

    return create_engine(url, connect_args=connect_args, **engine_kwargs)


def migrate_data(source_url: str, target_url: str, batch_size: int = 200) -> bool:
    """Migrates all data from source (SQLite) to target (PostgreSQL)."""
    logger.info("=" * 60)
    logger.info("🚀 Starting AgentForge Database Migration")
    logger.info(f"   Source : {source_url}")
    logger.info(f"   Target : {target_url.split('@')[-1] if '@' in target_url else target_url}")
    logger.info("=" * 60)

    source_engine = get_engine_for_url(source_url)
    target_engine = get_engine_for_url(target_url)

    # Test connections
    try:
        with source_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Connected to Source database.")
    except Exception as e:
        logger.error(f"❌ Cannot connect to source database: {e}")
        return False

    try:
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Connected to Target database.")
    except Exception as e:
        logger.error(f"❌ Cannot connect to target database: {e}")
        return False

    # Target PostgreSQL preparations: enable pgvector extension
    is_target_postgres = not str(target_engine.url).startswith("sqlite")
    if is_target_postgres:
        try:
            with target_engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            logger.info("✅ PostgreSQL vector extension verified/created.")
        except Exception as e:
            logger.warning(f"⚠️ Could not create vector extension (ensure pgvector is installed): {e}")

    # Build schema on target
    logger.info("📦 Ensuring schema and tables exist on target...")
    Base.metadata.create_all(bind=target_engine)
    logger.info("✅ Target schema verified.")

    # Create sessions
    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)
    src_db = SourceSession()
    tgt_db = TargetSession()

    counts: Dict[str, Dict[str, int]] = {
        "mcp_servers": {"source": 0, "migrated": 0, "skipped": 0},
        "tasks": {"source": 0, "migrated": 0, "skipped": 0},
        "subtasks": {"source": 0, "migrated": 0, "skipped": 0},
        "agent_logs": {"source": 0, "migrated": 0, "skipped": 0},
        "memories": {"source": 0, "migrated": 0, "skipped": 0},
    }

    try:
        # 1. MCP Servers
        logger.info("\n[1/5] Migrating MCP Servers...")
        try:
            mcp_items = src_db.query(MCPServer).all()
            counts["mcp_servers"]["source"] = len(mcp_items)
            for item in mcp_items:
                exists = tgt_db.query(MCPServer).filter(MCPServer.id == item.id).first()
                if not exists:
                    tgt_db.merge(MCPServer(
                        id=item.id,
                        name=item.name,
                        transport=item.transport,
                        command=item.command,
                        args=item.args,
                        url=item.url,
                        is_active=item.is_active
                    ))
                    counts["mcp_servers"]["migrated"] += 1
                else:
                    counts["mcp_servers"]["skipped"] += 1
            tgt_db.commit()
            logger.info(f"   MCP Servers: {counts['mcp_servers']['migrated']} migrated, {counts['mcp_servers']['skipped']} existing.")
        except Exception as e:
            logger.warning(f"   Skipping mcp_servers table: {e}")
            tgt_db.rollback()

        # 2. Tasks
        logger.info("\n[2/5] Migrating Tasks...")
        task_items = src_db.query(Task).all()
        counts["tasks"]["source"] = len(task_items)
        for t in task_items:
            exists = tgt_db.query(Task).filter(Task.id == t.id).first()
            if not exists:
                tgt_db.add(Task(
                    id=t.id,
                    prompt=t.prompt,
                    status=t.status,
                    plugin_name=t.plugin_name,
                    final_result=t.final_result,
                    total_tokens=t.total_tokens,
                    total_cost_usd=t.total_cost_usd,
                    total_latency_ms=t.total_latency_ms,
                    created_at=t.created_at,
                    updated_at=t.updated_at
                ))
                counts["tasks"]["migrated"] += 1
            else:
                counts["tasks"]["skipped"] += 1
        tgt_db.commit()
        logger.info(f"   Tasks: {counts['tasks']['migrated']} migrated, {counts['tasks']['skipped']} existing.")

        # 3. Subtasks
        logger.info("\n[3/5] Migrating Subtasks...")
        subtask_items = src_db.query(Subtask).all()
        counts["subtasks"]["source"] = len(subtask_items)
        for st in subtask_items:
            exists = tgt_db.query(Subtask).filter(Subtask.id == st.id).first()
            if not exists:
                tgt_db.add(Subtask(
                    id=st.id,
                    task_id=st.task_id,
                    title=st.title,
                    description=st.description,
                    assigned_agent=st.assigned_agent,
                    status=st.status,
                    output=st.output,
                    confidence_score=st.confidence_score,
                    order_index=st.order_index,
                    created_at=st.created_at
                ))
                counts["subtasks"]["migrated"] += 1
            else:
                counts["subtasks"]["skipped"] += 1
        tgt_db.commit()
        logger.info(f"   Subtasks: {counts['subtasks']['migrated']} migrated, {counts['subtasks']['skipped']} existing.")

        # 4. Agent Logs
        logger.info("\n[4/5] Migrating Agent Logs...")
        logs = src_db.query(AgentLog).all()
        counts["agent_logs"]["source"] = len(logs)
        existing_log_ids = {row[0] for row in tgt_db.query(AgentLog.id).all()}
        batch = []
        for l in logs:
            if l.id in existing_log_ids:
                counts["agent_logs"]["skipped"] += 1
                continue
            batch.append(AgentLog(
                id=l.id,
                task_id=l.task_id,
                subtask_id=l.subtask_id,
                agent_name=l.agent_name,
                log_type=l.log_type,
                content=l.content,
                prompt_tokens=l.prompt_tokens,
                completion_tokens=l.completion_tokens,
                total_tokens=l.total_tokens,
                latency_ms=l.latency_ms,
                cost_usd=l.cost_usd,
                created_at=l.created_at
            ))
            if len(batch) >= batch_size:
                tgt_db.bulk_save_objects(batch)
                tgt_db.commit()
                counts["agent_logs"]["migrated"] += len(batch)
                batch = []
        if batch:
            tgt_db.bulk_save_objects(batch)
            tgt_db.commit()
            counts["agent_logs"]["migrated"] += len(batch)
        logger.info(f"   Agent Logs: {counts['agent_logs']['migrated']} migrated, {counts['agent_logs']['skipped']} existing.")

        # 5. Memories (Vector Data)
        logger.info("\n[5/5] Migrating Memories & Vector Embeddings...")
        mems = src_db.query(Memory).all()
        counts["memories"]["source"] = len(mems)
        for m in mems:
            exists = tgt_db.query(Memory).filter(Memory.id == m.id).first()
            if not exists:
                tgt_db.add(Memory(
                    id=m.id,
                    category=m.category,
                    content=m.content,
                    embedding_searchable_text=m.embedding_searchable_text,
                    embedding=m.embedding,
                    created_at=m.created_at
                ))
                counts["memories"]["migrated"] += 1
            else:
                counts["memories"]["skipped"] += 1
        tgt_db.commit()
        logger.info(f"   Memories: {counts['memories']['migrated']} migrated, {counts['memories']['skipped']} existing.")

        # If PostgreSQL target, create HNSW vector index
        if is_target_postgres:
            logger.info("\n🔧 Building HNSW vector index on PostgreSQL memories...")
            try:
                with target_engine.connect() as conn:
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS ix_memories_embedding_hnsw "
                        "ON memories USING hnsw (embedding vector_cosine_ops);"
                    ))
                    conn.commit()
                logger.info("✅ HNSW Vector Index created successfully.")
            except Exception as ex:
                logger.warning(f"⚠️ Could not create HNSW index: {ex}")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 MIGRATION COMPLETE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"{'Table':<15} | {'Source':<8} | {'Migrated':<8} | {'Skipped':<8}")
        logger.info("-" * 47)
        for tbl, data in counts.items():
            logger.info(f"{tbl:<15} | {data['source']:<8} | {data['migrated']:<8} | {data['skipped']:<8}")
        logger.info("=" * 60)

        return True

    except Exception as err:
        logger.error(f"❌ Migration failed with error: {err}", exc_info=True)
        tgt_db.rollback()
        return False
    finally:
        src_db.close()
        tgt_db.close()


def main():
    parser = argparse.ArgumentParser(description="AgentForge SQLite to PostgreSQL Migration CLI")
    parser.add_argument(
        "--source",
        default="sqlite:///./agentforge.db",
        help="Source database URL (default: sqlite:///./agentforge.db)"
    )
    parser.add_argument(
        "--target",
        default=settings.database_url,
        help="Target PostgreSQL database URL (default: from settings/DATABASE_URL)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=250,
        help="Batch size for bulk log insertion"
    )

    args = parser.parse_args()

    target_url = args.target
    if not target_url or target_url.startswith("sqlite"):
        logger.error("❌ Please provide a valid target PostgreSQL URL using --target or the DATABASE_URL environment variable.")
        logger.error("Example: python -m backend.scripts.migrate_to_postgres --target postgresql://agentforge:agentforge_password@localhost:5432/agentforge")
        sys.exit(1)

    success = migrate_data(source_url=args.source, target_url=target_url, batch_size=args.batch_size)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
