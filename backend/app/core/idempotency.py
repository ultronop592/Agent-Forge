import re
import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.database.models import IdempotencyKey

IDEMPOTENCY_KEY_REGEX = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def validate_idempotency_key(key: str) -> None:
    if not key or not IDEMPOTENCY_KEY_REGEX.match(key):
        raise HTTPException(
            status_code=422,
            detail="Invalid Idempotency-Key format. Must be 8-128 characters matching [A-Za-z0-9_-]."
        )


def compute_request_hash(payload_dict: Dict[str, Any]) -> str:
    canonical_json = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_scope(api_key: Optional[str]) -> str:
    if api_key and api_key.strip():
        return hashlib.sha256(api_key.strip().encode("utf-8")).hexdigest()
    return "default_scope"


def clean_expired_keys(session: Session, limit: int = 100) -> None:
    try:
        now = datetime.utcnow()
        expired_ids = [
            row[0] for row in (
                session.query(IdempotencyKey.id)
                .filter(IdempotencyKey.expires_at < now)
                .limit(limit)
                .all()
            )
        ]
        if expired_ids:
            session.query(IdempotencyKey).filter(IdempotencyKey.id.in_(expired_ids)).delete(synchronize_session=False)
            session.commit()
    except Exception:
        session.rollback()
