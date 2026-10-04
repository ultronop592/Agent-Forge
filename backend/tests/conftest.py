import os
import sys

# On Python 3.14 on Windows, experimental mingw numpy crashes with access violation; block it in tests
if sys.version_info >= (3, 14):
    sys.modules["numpy"] = None

# Ensure unit tests use local sqlite and disable remote langsmith tracing by default
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_agentforge.db")
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

import pytest
from fastapi.testclient import TestClient

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.main import app
from backend.app.database.connection import Base, engine, SessionLocal

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure test database tables are created."""
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture
def db_session():
    """Provides a fresh database session for a test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def api_client():
    """Provides a FastAPI test client."""
    return TestClient(app)
