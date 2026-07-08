"""Alert and mass notification endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, TokenClaims, get_pagination, require_permissions
from app.models import Alert
from app.schemas.alert import AlertCreate, AlertResponse
from app.schemas.common import PaginatedResponse
from app.services.alert_service import AlertService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[AlertResponse])
async def list_alerts(
    client_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    incident_id: UUID | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("alerts:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(Alert).where(Alert.tenant_id == claims.tenant_id)
    if claims.client_id:
        q = q.where(Alert.client_id == claims.client_id)
    elif client_id:
        q = q.where(Alert.client_id == client_id)
    if status_filter:
        q = q.where(Alert.status == status_filter)
    if incident_id:
        q = q.where(Alert.incident_id == incident_id)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(Alert.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    alerts = (await db.execute(q)).scalars().all()

    return PaginatedResponse(data=alerts, total=total, page=pagination.page,
                             limit=pagination.limit, pages=-(-total // pagination.limit))


@router.post("", response_model=AlertResponse, status_code=201)
async def create_and_send_alert(
    body: AlertCreate,
    claims: TokenClaims = Depends(require_permissions("alerts:send")),
    db: AsyncSession = Depends(get_db),
):
    """Create an alert and immediately dispatch to recipients."""
    svc = AlertService(db, claims)
    return await svc.create_and_dispatch(body)


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    claims: TokenClaims = Depends(require_permissions("alerts:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.tenant_id == claims.tenant_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/resend", response_model=AlertResponse)
async def resend_alert(
    alert_id: UUID,
    claims: TokenClaims = Depends(require_permissions("alerts:send")),
    db: AsyncSession = Depends(get_db),
):
    """Resend a failed alert."""
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.tenant_id == claims.tenant_id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    svc = AlertService(db, claims)
    return await svc.dispatch_existing(alert)
