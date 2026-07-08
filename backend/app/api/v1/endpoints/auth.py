"""Authentication endpoints: login, refresh, logout, change password."""
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_claims, TokenClaims
from app.core.security import (
    build_token_payload,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models import User, UserSession
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.core.config import settings

router = APIRouter()

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": ["*"],
    "client_admin": [
        "clients:read", "users:manage", "sites:write", "assets:write",
        "incidents:create", "incidents:close", "alerts:send",
        "playbooks:execute", "playbooks:create", "tickets:create",
        "tickets:assign", "vulnerabilities:write", "contracts:read", "reports:compliance",
        "vision:read", "vision:write",
    ],
    "security_director": [
        "incidents:create", "incidents:close", "alerts:send", "playbooks:execute",
        "playbooks:create", "assets:read", "vulnerabilities:write", "reports:compliance",
        "vision:read", "vision:write",
    ],
    "soc_analyst": [
        "incidents:create", "incidents:close", "alerts:send", "playbooks:execute",
        "assets:read", "vulnerabilities:write", "tickets:create",
        "vision:read", "vision:write",
    ],
    "it_engineer": [
        "assets:write", "tickets:create", "tickets:assign",
        "vulnerabilities:write", "incidents:create",
        "vision:read", "vision:write",
    ],
    "field_technician": ["assets:read", "tickets:read_own", "vision:read"],
    "site_supervisor": ["incidents:read", "alerts:read", "vision:read"],
    "executive": ["incidents:read", "reports:read"],
    "auditor": ["incidents:read", "reports:compliance", "assets:read"],
}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account is {user.status}")

    permissions = ROLE_PERMISSIONS.get(user.role, [])
    payload = build_token_payload(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        permissions=permissions,
        client_id=user.client_id,
    )
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token({"sub": str(user.id), "tenant_id": str(user.tenant_id)})

    # Store refresh token hash
    session = UserSession(
        user_id=user.id,
        token_hash=_hash_token(refresh_token),
        ip_address=str(request.client.host) if request.client else None,
        device_info={"user_agent": request.headers.get("user-agent")},
        expires_at=datetime.now(timezone.utc).replace(
            second=0, microsecond=0
        ),  # set properly below
        created_at=datetime.now(timezone.utc),
    )
    from datetime import timedelta
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(session)

    # Update last login
    await db.execute(
        update(User).where(User.id == user.id).values(last_login_at=datetime.now(timezone.utc))
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    from jose import JWTError
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    token_hash = _hash_token(body.refresh_token)
    result = await db.execute(
        select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
    )
    session = result.scalar_one_or_none()
    if not session or not session.is_valid:
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    user_result = await db.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar_one_or_none()
    if not user or user.status != "active":
        raise HTTPException(status_code=401, detail="User unavailable")

    permissions = ROLE_PERMISSIONS.get(user.role, [])
    token_payload = build_token_payload(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
        permissions=permissions,
        client_id=user.client_id,
    )
    return TokenResponse(
        access_token=create_access_token(token_payload),
        refresh_token=body.refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    claims: TokenClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
):
    token_hash = _hash_token(body.refresh_token)
    await db.execute(
        update(UserSession)
        .where(UserSession.token_hash == token_hash, UserSession.user_id == claims.user_id)
        .values(revoked_at=datetime.now(timezone.utc))
    )


@router.get("/me")
async def get_me(
    claims: TokenClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == claims.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "client_id": str(user.client_id) if user.client_id else None,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "permissions": claims.permissions,
    }
