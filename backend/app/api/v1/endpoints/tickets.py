"""Work order / ticket endpoints."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, TokenClaims, get_pagination, require_permissions
from app.models import Ticket
from app.models.ticket import TicketComment
from app.schemas.common import PaginatedResponse
from app.schemas.ticket import (
    TicketCheckinRequest,
    TicketCheckoutRequest,
    TicketCommentCreate,
    TicketCreate,
    TicketResponse,
    TicketSignoffRequest,
    TicketUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TicketResponse])
async def list_tickets(
    client_id: UUID | None = Query(None),
    site_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    type_filter: str | None = Query(None, alias="type"),
    assigned_to: UUID | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("tickets:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(Ticket).where(Ticket.tenant_id == claims.tenant_id)
    if claims.client_id:
        q = q.where(Ticket.client_id == claims.client_id)
    elif client_id:
        q = q.where(Ticket.client_id == client_id)
    if site_id:
        q = q.where(Ticket.site_id == site_id)
    if status_filter:
        q = q.where(Ticket.status == status_filter)
    if priority:
        q = q.where(Ticket.priority == priority)
    if type_filter:
        q = q.where(Ticket.type == type_filter)
    if assigned_to:
        q = q.where(Ticket.assigned_to == assigned_to)
    elif "tickets:read_own" in (claims.permissions or []) and "*" not in (claims.permissions or []):
        q = q.where(Ticket.assigned_to == claims.user_id)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.order_by(Ticket.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    tickets = (await db.execute(q)).scalars().all()

    return PaginatedResponse(data=tickets, total=total, page=pagination.page,
                             limit=pagination.limit, pages=-(-total // pagination.limit))


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    body: TicketCreate,
    claims: TokenClaims = Depends(require_permissions("tickets:create")),
    db: AsyncSession = Depends(get_db),
):
    ticket = Ticket(
        tenant_id=claims.tenant_id,
        created_by=claims.user_id,
        **body.model_dump(),
    )
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: UUID,
    claims: TokenClaims = Depends(require_permissions("tickets:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == claims.tenant_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: UUID,
    body: TicketUpdate,
    claims: TokenClaims = Depends(require_permissions("tickets:create")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == claims.tenant_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ticket, field, value)
    if body.status == "resolved" and not ticket.resolved_at:
        ticket.resolved_at = datetime.now(timezone.utc)
    if body.status == "closed" and not ticket.closed_at:
        ticket.closed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/checkin", response_model=TicketResponse)
async def checkin(
    ticket_id: UUID,
    body: TicketCheckinRequest,
    claims: TokenClaims = Depends(require_permissions("tickets:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == claims.tenant_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.checkin_at = datetime.now(timezone.utc)
    ticket.status = "in_progress"
    if body.notes:
        comment = TicketComment(ticket_id=ticket_id, user_id=claims.user_id,
                                content=f"Checked in: {body.notes}", is_internal=True)
        db.add(comment)
    await db.flush()
    await db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/checkout", response_model=TicketResponse)
async def checkout(
    ticket_id: UUID,
    body: TicketCheckoutRequest,
    claims: TokenClaims = Depends(require_permissions("tickets:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == claims.tenant_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.checkout_at = datetime.now(timezone.utc)
    ticket.status = "resolved"
    ticket.resolved_at = datetime.now(timezone.utc)
    if body.resolution_notes:
        ticket.resolution_notes = body.resolution_notes
    if body.labor_hours:
        ticket.labor_hours = body.labor_hours
    if body.parts_used:
        ticket.parts_used = body.parts_used
    await db.flush()
    await db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/signoff", response_model=TicketResponse)
async def client_signoff(
    ticket_id: UUID,
    body: TicketSignoffRequest,
    claims: TokenClaims = Depends(require_permissions("tickets:create")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == claims.tenant_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.client_signoff_at = datetime.now(timezone.utc)
    ticket.client_signoff_by = body.signed_by
    ticket.status = "closed"
    ticket.closed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/comments", status_code=201)
async def add_comment(
    ticket_id: UUID,
    body: TicketCommentCreate,
    claims: TokenClaims = Depends(require_permissions("tickets:read")),
    db: AsyncSession = Depends(get_db),
):
    comment = TicketComment(
        ticket_id=ticket_id,
        user_id=claims.user_id,
        content=body.content,
        is_internal=body.is_internal,
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    return {"id": str(comment.id), "content": comment.content}
