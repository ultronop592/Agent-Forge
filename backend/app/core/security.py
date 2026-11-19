import hmac
import hashlib
from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def hash_key_identifier(key: Optional[str]) -> str:
    if not key:
        return "anonymous"
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()[:16]


async def verify_api_key(
    x_api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> bool:
    secret_key = settings.api_secret_key
    if not secret_key:
        return True

    provided_token = x_api_key
    if not provided_token and credentials:
        provided_token = credentials.credentials

    if provided_token and hmac.compare_digest(provided_token.strip(), secret_key.strip()):
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Secret Key. Provide a valid 'X-API-Key' header or 'Bearer' token."
    )


async def verify_admin_key(
    x_admin_key: Optional[str] = Security(admin_key_header)
) -> str:
    admin_secret = settings.admin_api_key
    if not admin_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin API Key is not configured on this server. Administrative operations are disabled."
        )

    if not x_admin_key or not hmac.compare_digest(x_admin_key.strip(), admin_secret.strip()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-Key header."
        )

    return hash_key_identifier(x_admin_key)
