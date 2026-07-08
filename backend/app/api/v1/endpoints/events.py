"""Security event ingestion endpoint — receives events from integrations."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TokenClaims, get_current_claims
from app.models.event import SecurityEvent
from app.schemas.event import EventIngest, EventResponse

router = APIRouter()


@router.post("/ingest", response_model=EventResponse, status_code=202)
async def ingest_event(
    body: EventIngest,
    claims: TokenClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a security event from an integration (NVR, access control, EDR, etc.)
    and queue it for processing. Returns immediately with 202 Accepted.

    The Celery worker will:
    1. Store in Elasticsearch (for SOC search)
    2. Evaluate against active playbooks
    3. Create incidents / alerts / tickets as configured
    """
    event = SecurityEvent(
        tenant_id=claims.tenant_id,
        client_id=body.client_id,
        site_id=body.site_id,
        asset_id=body.asset_id,
        event_type=body.event_type,
        source_type=body.source_type,
        source_name=body.source_name,
        severity=body.severity,
        raw_data=body.raw_data,
        normalized_data=body.normalized_data,
        created_at=body.occurred_at or datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)

    # Queue async processing
    from app.workers.tasks import process_security_event
    process_security_event.delay(str(event.id))

    return event
