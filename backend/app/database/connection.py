from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.core.config import settings

connect_args = {}
engine_kwargs = {}

# SQLite specific config
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # PostgreSQL / Neon optimization:
    # Serverless databases aggressively close idle connections. pool_pre_ping tests connection health.
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_db_schema():
    """Ensure newly added columns exist in SQLite or PostgreSQL."""
    from sqlalchemy import text
    is_sqlite = str(engine.url).startswith("sqlite")
    
    task_cols = [
        ("total_tokens", "INTEGER DEFAULT 0"),
        ("total_cost_usd", "FLOAT DEFAULT 0.0"),
        ("total_latency_ms", "FLOAT DEFAULT 0.0"),
    ]
    
    log_cols = [
        ("prompt_tokens", "INTEGER DEFAULT 0"),
        ("completion_tokens", "INTEGER DEFAULT 0"),
        ("total_tokens", "INTEGER DEFAULT 0"),
        ("latency_ms", "FLOAT DEFAULT 0.0"),
        ("cost_usd", "FLOAT DEFAULT 0.0"),
    ]
    
    try:
        if is_sqlite:
            with engine.connect() as conn:
                for col_name, col_type in task_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass

                for col_name, col_type in log_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE agent_logs ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass
        else:
            with engine.connect() as conn:
                # Query existing columns in tasks
                res_tasks = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='tasks'")).fetchall()
                existing_task_cols = {row[0] for row in res_tasks}
                for col_name, col_type in task_cols:
                    if col_name not in existing_task_cols:
                        conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}"))
                        conn.commit()

                # Query existing columns in agent_logs
                res_logs = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='agent_logs'")).fetchall()
                existing_log_cols = {row[0] for row in res_logs}
                for col_name, col_type in log_cols:
                    if col_name not in existing_log_cols:
                        conn.execute(text(f"ALTER TABLE agent_logs ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
    except Exception:
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Auto-migrate newly added telemetry columns
ensure_db_schema()

