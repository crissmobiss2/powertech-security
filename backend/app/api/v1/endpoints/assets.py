"""Asset (CMDB) management endpoints."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, TokenClaims, get_pagination, require_permissions
from app.models import Asset
from app.schemas.asset import AssetCreate, AssetResponse, AssetStatusUpdate, AssetUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[AssetResponse])
async def list_assets(
    client_id: UUID | None = Query(None),
    site_id: UUID | None = Query(None),
    type_filter: str | None = Query(None, alias="type"),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("assets:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(Asset).where(
        Asset.tenant_id == claims.tenant_id,
        Asset.deleted_at.is_(None),
    )
    if claims.client_id:
        q = q.where(Asset.client_id == claims.client_id)
    elif client_id:
        q = q.where(Asset.client_id == client_id)
    if site_id:
        q = q.where(Asset.site_id == site_id)
    if type_filter:
        q = q.where(Asset.type == type_filter)
    if status_filter:
        q = q.where(Asset.status == status_filter)
    if search:
        q = q.where(Asset.name.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(Asset.name).offset(pagination.offset).limit(pagination.limit)
    assets = (await db.execute(q)).scalars().all()

    return PaginatedResponse(data=assets, total=total, page=pagination.page,
                             limit=pagination.limit, pages=-(-total // pagination.limit))


@router.post("", response_model=AssetResponse, status_code=201)
async def create_asset(
    body: AssetCreate,
    claims: TokenClaims = Depends(require_permissions("assets:write")),
    db: AsyncSession = Depends(get_db),
):
    asset = Asset(
        tenant_id=claims.tenant_id,
        created_by=claims.user_id,
        **body.model_dump(),
    )
    db.add(asset)
    await db.flush()
    await db.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    claims: TokenClaims = Depends(require_permissions("assets:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.tenant_id == claims.tenant_id,
                            Asset.deleted_at.is_(None))
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: UUID,
    body: AssetUpdate,
    claims: TokenClaims = Depends(require_permissions("assets:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.tenant_id == claims.tenant_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(asset, field, value)
    await db.flush()
    await db.refresh(asset)
    return asset


@router.patch("/{asset_id}/status", response_model=AssetResponse)
async def update_asset_status(
    asset_id: UUID,
    body: AssetStatusUpdate,
    claims: TokenClaims = Depends(require_permissions("assets:write")),
    db: AsyncSession = Depends(get_db),
):
    """Update just the status of an asset (used by integrations and health checks)."""
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.tenant_id == claims.tenant_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    old_status = asset.status
    asset.status = body.status
    asset.last_seen_at = body.last_seen_at or datetime.now(timezone.utc)
    await db.flush()

    # Emit a security event for status changes (processed by automation engine)
    if old_status != body.status:
        from app.models.event import SecurityEvent
        event = SecurityEvent(
            tenant_id=claims.tenant_id,
            client_id=asset.client_id,
            site_id=asset.site_id,
            asset_id=asset.id,
            event_type=f"asset.{body.status}",
            source_type="api",
            source_name="status_update",
            severity="high" if body.status == "offline" else "info",
            normalized_data={"asset_id": str(asset.id), "old_status": old_status, "new_status": body.status},
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.flush()

        # Queue for automation processing
        from app.workers.tasks import process_security_event
        process_security_event.delay(str(event.id))

    await db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: UUID,
    claims: TokenClaims = Depends(require_permissions("assets:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.tenant_id == claims.tenant_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset.deleted_at = datetime.now(timezone.utc)
