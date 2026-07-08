"""Site management endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, TokenClaims, get_pagination, require_permissions
from app.models import Site
from app.schemas.common import PaginatedResponse
from app.schemas.site import SiteCreate, SiteResponse, SiteUpdate

router = APIRouter()


def _base_query(claims: TokenClaims):
    q = select(Site).where(
        Site.tenant_id == claims.tenant_id,
        Site.deleted_at.is_(None),
    )
    if claims.client_id:
        q = q.where(Site.client_id == claims.client_id)
    return q


@router.get("", response_model=PaginatedResponse[SiteResponse])
async def list_sites(
    client_id: UUID | None = Query(None),
    risk_level: str | None = Query(None),
    type_filter: str | None = Query(None, alias="type"),
    search: str | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("sites:read")),
    db: AsyncSession = Depends(get_db),
):
    q = _base_query(claims)
    if client_id:
        q = q.where(Site.client_id == client_id)
    if risk_level:
        q = q.where(Site.risk_level == risk_level)
    if type_filter:
        q = q.where(Site.type == type_filter)
    if search:
        q = q.where(Site.name.ilike(f"%{search}%"))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(Site.name).offset(pagination.offset).limit(pagination.limit)
    sites = (await db.execute(q)).scalars().all()

    return PaginatedResponse(data=sites, total=total, page=pagination.page,
                             limit=pagination.limit, pages=-(-total // pagination.limit))


@router.post("", response_model=SiteResponse, status_code=201)
async def create_site(
    body: SiteCreate,
    claims: TokenClaims = Depends(require_permissions("sites:write")),
    db: AsyncSession = Depends(get_db),
):
    site = Site(tenant_id=claims.tenant_id, **body.model_dump())
    db.add(site)
    await db.flush()
    await db.refresh(site)
    return site


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: UUID,
    claims: TokenClaims = Depends(require_permissions("sites:read")),
    db: AsyncSession = Depends(get_db),
):
    q = _base_query(claims).where(Site.id == site_id)
    site = (await db.execute(q)).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: UUID,
    body: SiteUpdate,
    claims: TokenClaims = Depends(require_permissions("sites:write")),
    db: AsyncSession = Depends(get_db),
):
    q = _base_query(claims).where(Site.id == site_id)
    site = (await db.execute(q)).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(site, field, value)
    await db.flush()
    await db.refresh(site)
    return site


@router.delete("/{site_id}", status_code=204)
async def delete_site(
    site_id: UUID,
    claims: TokenClaims = Depends(require_permissions("sites:write")),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    q = _base_query(claims).where(Site.id == site_id)
    site = (await db.execute(q)).scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    site.deleted_at = datetime.now(timezone.utc)
