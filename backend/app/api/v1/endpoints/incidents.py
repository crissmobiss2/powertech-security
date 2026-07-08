"""Incident lifecycle management endpoints."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, TokenClaims, get_pagination, require_permissions
from app.models import Incident
from app.models.incident import IncidentTimeline
from app.schemas.common import PaginatedResponse
from app.schemas.incident import (
    CommentCreate,
    IncidentCloseRequest,
    IncidentCreate,
    IncidentResponse,
    IncidentTimelineEntry,
    IncidentUpdate,
)
from app.services.incident_service import IncidentService

router = APIRouter()


def _base_q(claims: TokenClaims):
    q = select(Incident).where(Incident.tenant_id == claims.tenant_id)
    if claims.client_id:
        q = q.where(Incident.client_id == claims.client_id)
    return q


@router.get("", response_model=PaginatedResponse[IncidentResponse])
async def list_incidents(
    client_id: UUID | None = Query(None),
    site_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    severity: str | None = Query(None),
    type_filter: str | None = Query(None, alias="type"),
    assigned_to: UUID | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("incidents:read")),
    db: AsyncSession = Depends(get_db),
):
    q = _base_q(claims)
    if client_id and not claims.client_id:
        q = q.where(Incident.client_id == client_id)
    if site_id:
        q = q.where(Incident.site_id == site_id)
    if status_filter:
        q = q.where(Incident.status == status_filter)
    if severity:
        q = q.where(Incident.severity == severity)
    if type_filter:
        q = q.where(Incident.type == type_filter)
    if assigned_to:
        q = q.where(Incident.assigned_to == assigned_to)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(Incident.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    incidents = (await db.execute(q)).scalars().all()

    return PaginatedResponse(data=incidents, total=total, page=pagination.page,
                             limit=pagination.limit, pages=-(-total // pagination.limit))


@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(
    body: IncidentCreate,
    claims: TokenClaims = Depends(require_permissions("incidents:create")),
    db: AsyncSession = Depends(get_db),
):
    svc = IncidentService(db, claims)
    return await svc.create(body)


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: UUID,
    claims: TokenClaims = Depends(require_permissions("incidents:read")),
    db: AsyncSession = Depends(get_db),
):
    q = _base_q(claims).where(Incident.id == incident_id)
    incident = (await db.execute(q)).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.put("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    body: IncidentUpdate,
    claims: TokenClaims = Depends(require_permissions("incidents:create")),
    db: AsyncSession = Depends(get_db),
):
    svc = IncidentService(db, claims)
    return await svc.update(incident_id, body)


@router.post("/{incident_id}/acknowledge", response_model=IncidentResponse)
async def acknowledge_incident(
    incident_id: UUID,
    claims: TokenClaims = Depends(require_permissions("incidents:create")),
    db: AsyncSession = Depends(get_db),
):
    svc = IncidentService(db, claims)
    return await svc.acknowledge(incident_id)


@router.post("/{incident_id}/close", response_model=IncidentResponse)
async def close_incident(
    incident_id: UUID,
    body: IncidentCloseRequest,
    claims: TokenClaims = Depends(require_permissions("incidents:close")),
    db: AsyncSession = Depends(get_db),
):
    svc = IncidentService(db, claims)
    return await svc.close(incident_id, body)


@router.get("/{incident_id}/timeline", response_model=list[IncidentTimelineEntry])
async def get_timeline(
    incident_id: UUID,
    claims: TokenClaims = Depends(require_permissions("incidents:read")),
    db: AsyncSession = Depends(get_db),
):
    q = _base_q(claims).where(Incident.id == incident_id)
    incident = (await db.execute(q)).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    result = await db.execute(
        select(IncidentTimeline)
        .where(IncidentTimeline.incident_id == incident_id)
        .order_by(IncidentTimeline.created_at)
    )
    return result.scalars().all()


@router.post("/{incident_id}/comments", response_model=IncidentTimelineEntry, status_code=201)
async def add_comment(
    incident_id: UUID,
    body: CommentCreate,
    claims: TokenClaims = Depends(require_permissions("incidents:create")),
    db: AsyncSession = Depends(get_db),
):
    q = _base_q(claims).where(Incident.id == incident_id)
    incident = (await db.execute(q)).scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    entry = IncidentTimeline(
        incident_id=incident_id,
        tenant_id=claims.tenant_id,
        user_id=claims.user_id,
        event_type="commented",
        description=body.description,
        metadata=body.metadata,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry
