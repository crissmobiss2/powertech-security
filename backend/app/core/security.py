"""JWT creation/validation and password hashing."""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(payload: dict[str, Any]) -> str:
    data = payload.copy()
    data["exp"] = _now_utc() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    data["type"] = "access"
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(payload: dict[str, Any]) -> str:
    data = payload.copy()
    data["exp"] = _now_utc() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    data["type"] = "refresh"
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Raises JWTError if invalid or expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def build_token_payload(
    user_id: UUID,
    tenant_id: UUID,
    role: str,
    permissions: list[str],
    client_id: UUID | None = None,
) -> dict[str, Any]:
    return {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "client_id": str(client_id) if client_id else None,
        "role": role,
        "permissions": permissions,
    }
