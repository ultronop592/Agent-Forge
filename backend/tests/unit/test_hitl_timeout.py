import pytest
from backend.app.core.config import settings

def test_hitl_timeout_config():
    assert hasattr(settings, "hitl_timeout_seconds")
    assert settings.hitl_timeout_seconds == 60.0
