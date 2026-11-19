import os
import sys
from typing import List
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.config import settings


def check_index() -> None:
    db_url = os.environ.get("DATABASE_URL") or settings.database_url
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    print("=" * 60)
    print("AgentForge PostgreSQL HNSW Index Diagnostics")
    print("=" * 60)
    print(f"Target Database URL: {db_url.split('@')[-1] if '@' in db_url else db_url}")

    if not db_url.startswith("postgresql"):
        print("[INFO] Database dialect is not PostgreSQL (e.g. SQLite).")
        print("[INFO] HNSW index is supported only on PostgreSQL with pgvector.")
        print("[INFO] Local SQLite uses NumPy/pure-Python scan.")
        print("=" * 60)
        return

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            print("\n--- Step 1: Extension and Schema Verification ---")
            ext = conn.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")).fetchone()
            if ext:
                print(f"[OK] pgvector extension installed: version {ext[1]}")
            else:
                print("[FAIL] pgvector extension NOT installed.")
                print("Run SQL: CREATE EXTENSION IF NOT EXISTS vector;")

            col = conn.execute(text(
                "SELECT column_name, data_type, udt_name FROM information_schema.columns "
                "WHERE table_name = 'memories' AND column_name = 'embedding';"
            )).fetchone()
            if col:
                print(f"[OK] memories.embedding column found: data_type={col[1]}, udt_name={col[2]}")
            else:
                print("[FAIL] memories.embedding column missing.")

            idx = conn.execute(text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename = 'memories' AND indexname = 'ix_memories_embedding_hnsw';"
            )).fetchone()
            if idx:
                print(f"[OK] HNSW index found: {idx[0]}")
                print(f"     Definition: {idx[1]}")
            else:
                print("[FAIL] ix_memories_embedding_hnsw index NOT found.")
                print("Run SQL: CREATE INDEX IF NOT EXISTS ix_memories_embedding_hnsw ON memories USING hnsw (embedding vector_cosine_ops);")

            row_count = conn.execute(text("SELECT COUNT(*) FROM memories;")).scalar() or 0
            print(f"[INFO] Total rows in memories table: {row_count}")

            print("\n--- Step 2: Query Plan Analysis (EXPLAIN) ---")
            dummy_vec: List[str] = ["0.01"] * 768
            vec_literal = "[" + ",".join(dummy_vec) + "]"
            query = f"EXPLAIN (FORMAT TEXT) SELECT id FROM memories ORDER BY embedding <=> '{vec_literal}'::vector LIMIT 5;"

            try:
                plan_rows = conn.execute(text(query)).fetchall()
                full_plan = "\n".join(r[0] for r in plan_rows)
                print("Standard Planner Execution Plan:")
                print(full_plan)

                if "ix_memories_embedding_hnsw" in full_plan:
                    print("\n[SUCCESS] ix_memories_embedding_hnsw index is actively used in standard plan!")
                else:
                    print("\n[NOTE] Standard plan did not use HNSW index (likely due to small row count).")
                    print("Testing forced index plan with SET LOCAL enable_seqscan = off...")
                    with conn.begin():
                        conn.execute(text("SET LOCAL enable_seqscan = off;"))
                        forced_rows = conn.execute(text(query)).fetchall()
                        forced_plan = "\n".join(r[0] for r in forced_rows)
                        print("\nForced Index Plan:")
                        print(forced_plan)
                        if "ix_memories_embedding_hnsw" in forced_plan:
                            print("\n[SUCCESS] Verified: HNSW index is valid and recognized by PostgreSQL query planner.")
                        else:
                            print("\n[WARNING] HNSW index was not used even with enable_seqscan=off.")
            except Exception as e:
                print(f"[ERROR] Failed to run EXPLAIN query: {e}")
    except Exception as conn_err:
        print(f"[ERROR] Could not connect to database: {conn_err}")

    print("=" * 60)


if __name__ == "__main__":
    check_index()
