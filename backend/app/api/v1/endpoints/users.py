"""User management endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, TokenClaims, get_pagination, require_permissions
from app.core.security import hash_password
from app.models import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    role: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    client_id: UUID | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("users:manage")),
    db: AsyncSession = Depends(get_db),
):
    q = select(User).where(
        User.tenant_id == claims.tenant_id,
        User.deleted_at.is_(None),
    )
    if claims.client_id:
        q = q.where(User.client_id == claims.client_id)
    elif client_id:
        q = q.where(User.client_id == client_id)
    if role:
        q = q.where(User.role == role)
    if status_filter:
        q = q.where(User.status == status_filter)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(User.last_name).offset(pagination.offset).limit(pagination.limit)
    users = (await db.execute(q)).scalars().all()

    return PaginatedResponse(data=users, total=total, page=pagination.page,
                             limit=pagination.limit, pages=-(-total // pagination.limit))


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    body: UserCreate,
    claims: TokenClaims = Depends(require_permissions("users:manage")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(User).where(User.email == body.email, User.tenant_id == claims.tenant_id,
                           User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user_data = body.model_dump()
    plain_pw = user_data.pop("password")
    user = User(
        tenant_id=claims.tenant_id,
        password_hash=hash_password(plain_pw),
        **user_data,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    claims: TokenClaims = Depends(require_permissions("users:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == claims.tenant_id,
                           User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    claims: TokenClaims = Depends(require_permissions("users:manage")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == claims.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return user
