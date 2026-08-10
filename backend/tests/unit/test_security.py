import pytest
from fastapi import HTTPException
from backend.app.core.config import settings
from backend.app.core.security import verify_api_key

@pytest.mark.asyncio
async def test_verify_api_key_permissive_when_empty():
    settings.api_secret_key = ""
    # Should allow request when API_SECRET_KEY is empty
    result = await verify_api_key(x_api_key=None, credentials=None)
    assert result is True

@pytest.mark.asyncio
async def test_verify_api_key_valid_header():
    settings.api_secret_key = "test-secret-key-123"
    result = await verify_api_key(x_api_key="test-secret-key-123", credentials=None)
    assert result is True

@pytest.mark.asyncio
async def test_verify_api_key_invalid_header():
    settings.api_secret_key = "test-secret-key-123"
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key(x_api_key="wrong-key", credentials=None)
    assert exc_info.value.status_code == 401
    settings.api_secret_key = ""  # Reset after test
