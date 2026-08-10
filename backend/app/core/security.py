from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

async def verify_api_key(
    x_api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> bool:
    """
    Verifies incoming request API key.
    If API_SECRET_KEY is configured in backend environment, enforces key verification.
    If API_SECRET_KEY is empty/unset, allows requests to pass (permissive deployment default).
    """
    secret_key = settings.api_secret_key
    if not secret_key:
        # Public / open access mode (when no API_SECRET_KEY is set in environment)
        return True

    provided_token = x_api_key
    if not provided_token and credentials:
        provided_token = credentials.credentials

    if provided_token == secret_key:
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Secret Key. Provide a valid 'X-API-Key' header or 'Bearer' token."
    )
