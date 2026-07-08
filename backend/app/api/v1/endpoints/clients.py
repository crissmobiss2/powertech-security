"""Client management endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, TokenClaims, get_pagination, require_permissions
from app.models import Client
from app.schemas.client import ClientCreate, ClientResponse, ClientUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ClientResponse])
async def list_clients(
    status_filter: str | None = Query(None, alias="status"),
    risk_tier: str | None = Query(None),
    search: str | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("clients:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(Client).where(
        Client.tenant_id == claims.tenant_id,
        Client.deleted_at.is_(None),
    )
    if claims.client_id:
        q = q.where(Client.id == claims.client_id)
    if status_filter:
        q = q.where(Client.status == status_filter)
    if risk_tier:
        q = q.where(Client.risk_tier == risk_tier)
    if search:
        q = q.where(Client.name.ilike(f"%{search}%"))

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(Client.name).offset(pagination.offset).limit(pagination.limit)
    result = await db.execute(q)
    clients = result.scalars().all()

    return PaginatedResponse(
        data=clients,
        total=total,
        page=pagination.page,
        limit=pagination.limit,
        pages=-(-total // pagination.limit),
    )


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    body: ClientCreate,
    claims: TokenClaims = Depends(require_permissions("clients:write")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Client).where(Client.code == body.code, Client.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Client code '{body.code}' already exists")

    client = Client(
        tenant_id=claims.tenant_id,
        **body.model_dump(),
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    claims: TokenClaims = Depends(require_permissions("clients:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.tenant_id == claims.tenant_id,
            Client.deleted_at.is_(None),
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    body: ClientUpdate,
    claims: TokenClaims = Depends(require_permissions("clients:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == claims.tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(client, field, value)

    await db.flush()
    await db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: UUID,
    claims: TokenClaims = Depends(require_permissions("clients:write")),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == claims.tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.deleted_at = datetime.now(timezone.utc)
