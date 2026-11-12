import pytest
from fastapi import HTTPException
from backend.app.core.config import settings
from backend.app.core.security import verify_api_key

@pytest.mark.asyncio
async def test_verify_api_key_permissive_when_empty() -> None:
    settings.api_secret_key = ""
    result = await verify_api_key(x_api_key=None, credentials=None)
    assert result is True

@pytest.mark.asyncio
async def test_verify_api_key_valid_header() -> None:
    settings.api_secret_key = "test-secret-key-123"
    result = await verify_api_key(x_api_key="test-secret-key-123", credentials=None)
    assert result is True

@pytest.mark.asyncio
async def test_verify_api_key_invalid_header() -> None:
    settings.api_secret_key = "test-secret-key-123"
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(x_api_key="wrong-key", credentials=None)
    assert exc_info.value.status_code == 401
    settings.api_secret_key = ""


def test_validate_allowed_origins_wildcard() -> None:
    from backend.app.main import validate_allowed_origins
    warning = validate_allowed_origins(["*"])
    assert warning is not None
    assert "ALLOWED_ORIGINS contains wildcard '*'" in warning


def test_validate_allowed_origins_empty() -> None:
    from backend.app.main import validate_allowed_origins
    warning = validate_allowed_origins([])
    assert warning is not None
    assert "ALLOWED_ORIGINS is empty" in warning


def test_validate_allowed_origins_explicit() -> None:
    from backend.app.main import validate_allowed_origins
    warning = validate_allowed_origins(["https://agentforge.vercel.app", "http://localhost:3000"])
    assert warning is None


def test_production_refuses_to_start_with_empty_origins() -> None:
    from backend.app.main import validate_allowed_origins
    with pytest.raises(RuntimeError, match="Refusing to start in production environment"):
        validate_allowed_origins([], environment="production")


def test_production_refuses_to_start_with_wildcard_origins() -> None:
    from backend.app.main import validate_allowed_origins
    with pytest.raises(RuntimeError, match="Refusing to start in production environment"):
        validate_allowed_origins(["*"], environment="production")


def test_production_allows_explicit_origins() -> None:
    from backend.app.main import validate_allowed_origins
    warning = validate_allowed_origins(["https://agentforge.vercel.app"], environment="production")
    assert warning is None

