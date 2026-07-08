"""FastAPI dependency injection: auth, tenant scoping, pagination."""
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

bearer_scheme = HTTPBearer()


@dataclass
class TokenClaims:
    user_id: UUID
    tenant_id: UUID
    client_id: UUID | None
    role: str
    permissions: list[str]


@dataclass
class PaginationParams:
    page: int
    limit: int
    offset: int


def get_pagination(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    return PaginationParams(page=page, limit=limit, offset=(page - 1) * limit)


def get_current_claims(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenClaims:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise credentials_exception
        return TokenClaims(
            user_id=UUID(payload["sub"]),
            tenant_id=UUID(payload["tenant_id"]),
            client_id=UUID(payload["client_id"]) if payload.get("client_id") else None,
            role=payload["role"],
            permissions=payload.get("permissions", []),
        )
    except (JWTError, KeyError, ValueError):
        raise credentials_exception


def require_permissions(*required: str):
    """Factory: returns a dependency that checks the caller has ALL required permissions."""
    def checker(claims: TokenClaims = Depends(get_current_claims)) -> TokenClaims:
        if claims.role == "super_admin":
            return claims
        missing = [p for p in required if p not in claims.permissions]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )
        return claims
    return checker


def require_roles(*allowed_roles: str):
    """Factory: returns a dependency that checks the caller's role is in allowed_roles."""
    def checker(claims: TokenClaims = Depends(get_current_claims)) -> TokenClaims:
        if claims.role not in allowed_roles and claims.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this operation",
            )
        return claims
    return checker
