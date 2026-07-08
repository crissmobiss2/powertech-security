"""SOAR automation playbook endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, TokenClaims, get_pagination, require_permissions
from app.models import Playbook
from app.models.playbook import PlaybookExecution
from app.schemas.common import PaginatedResponse
from app.schemas.playbook import (
    PlaybookCreate,
    PlaybookExecuteRequest,
    PlaybookExecutionResponse,
    PlaybookResponse,
    PlaybookUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[PlaybookResponse])
async def list_playbooks(
    trigger_type: str | None = Query(None),
    enabled: bool | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("playbooks:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(Playbook).where(Playbook.tenant_id == claims.tenant_id)
    if trigger_type:
        q = q.where(Playbook.trigger_type == trigger_type)
    if enabled is not None:
        q = q.where(Playbook.enabled == enabled)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(Playbook.name).offset(pagination.offset).limit(pagination.limit)
    playbooks = (await db.execute(q)).scalars().all()

    return PaginatedResponse(data=playbooks, total=total, page=pagination.page,
                             limit=pagination.limit, pages=-(-total // pagination.limit))


@router.post("", response_model=PlaybookResponse, status_code=201)
async def create_playbook(
    body: PlaybookCreate,
    claims: TokenClaims = Depends(require_permissions("playbooks:create")),
    db: AsyncSession = Depends(get_db),
):
    playbook = Playbook(
        tenant_id=claims.tenant_id,
        created_by=claims.user_id,
        **body.model_dump(),
    )
    db.add(playbook)
    await db.flush()
    await db.refresh(playbook)
    return playbook


@router.get("/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(
    playbook_id: UUID,
    claims: TokenClaims = Depends(require_permissions("playbooks:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Playbook).where(Playbook.id == playbook_id, Playbook.tenant_id == claims.tenant_id)
    )
    pb = result.scalar_one_or_none()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return pb


@router.put("/{playbook_id}", response_model=PlaybookResponse)
async def update_playbook(
    playbook_id: UUID,
    body: PlaybookUpdate,
    claims: TokenClaims = Depends(require_permissions("playbooks:create")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Playbook).where(Playbook.id == playbook_id, Playbook.tenant_id == claims.tenant_id)
    )
    pb = result.scalar_one_or_none()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(pb, field, value)
    await db.flush()
    await db.refresh(pb)
    return pb


@router.post("/{playbook_id}/execute", response_model=PlaybookExecutionResponse, status_code=202)
async def execute_playbook(
    playbook_id: UUID,
    body: PlaybookExecuteRequest,
    claims: TokenClaims = Depends(require_permissions("playbooks:execute")),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a playbook execution."""
    from app.services.automation_service import AutomationService
    svc = AutomationService(db, claims)
    return await svc.execute_playbook(playbook_id, body.trigger_event, body.incident_id)


@router.get("/{playbook_id}/executions", response_model=list[PlaybookExecutionResponse])
async def list_executions(
    playbook_id: UUID,
    claims: TokenClaims = Depends(require_permissions("playbooks:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlaybookExecution)
        .where(PlaybookExecution.playbook_id == playbook_id,
               PlaybookExecution.tenant_id == claims.tenant_id)
        .order_by(PlaybookExecution.started_at.desc())
        .limit(50)
    )
    return result.scalars().all()
