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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

