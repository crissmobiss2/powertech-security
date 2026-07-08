"""Threat response action endpoints — lockdown, dispatch, notify, etc."""
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import TokenClaims, require_permissions
from app.models.vision import ThreatDetection
from app.models.incident import Incident

logger = logging.getLogger(__name__)
router = APIRouter()


class ThreatResponseAction(BaseModel):
    action: str = Field(pattern="^(lockdown|dispatch_security|notify_police|sound_alarm|evacuate|all_clear|isolate_zone|notify_management)$")
    threat_id: UUID
    notes: str | None = None
    zone: str | None = None


class ThreatResponseResult(BaseModel):
    action: str
    status: str
    threat_id: UUID
    triggered_at: str
    message: str


class BulkThreatAction(BaseModel):
    threat_ids: list[UUID]
    action: str = Field(pattern="^(acknowledge|resolve|false_positive|escalate)$")
    notes: str | None = None


@router.post("/respond", response_model=ThreatResponseResult)
async def execute_threat_response(
    body: ThreatResponseAction,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_permissions("vision:write")),
):
    result = await db.execute(
        select(ThreatDetection).where(
            ThreatDetection.id == body.threat_id,
            ThreatDetection.tenant_id == claims.tenant_id,
        )
    )
    threat = result.scalar_one_or_none()
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")

    now = datetime.now(timezone.utc)
    existing_actions = threat.response_actions or []
    existing_actions.append({
        "action": body.action,
        "status": "triggered",
        "triggered_by": str(claims.user_id),
        "triggered_at": now.isoformat(),
        "notes": body.notes,
        "zone": body.zone or threat.zone,
    })
    threat.response_actions = existing_actions
    threat.auto_response_triggered = True

    messages = {
        "lockdown": f"LOCKDOWN initiated for zone: {body.zone or threat.zone or 'ALL'}",
        "dispatch_security": "Security team dispatched to threat location",
        "notify_police": "Philippine National Police notified — awaiting response",
        "sound_alarm": "Site alarm activated",
        "evacuate": f"Evacuation order issued for zone: {body.zone or threat.zone or 'ALL'}",
        "all_clear": "All-clear signal broadcast — threat neutralized",
        "isolate_zone": f"Zone {body.zone or threat.zone or 'UNKNOWN'} isolated — access restricted",
        "notify_management": "Management team alerted via SMS and email",
    }

    if body.action == "all_clear":
        threat.status = "resolved"
        threat.resolved_at = now

    try:
        from app.services.ws_manager import publish_event
        await publish_event(
            "vision:system", "response_action",
            {
                "action": body.action,
                "threat_id": str(body.threat_id),
                "zone": body.zone or threat.zone,
                "message": messages.get(body.action, "Action executed"),
                "triggered_by": str(claims.user_id),
            },
            claims.tenant_id,
        )
    except Exception:
        logger.debug("WebSocket publish failed", exc_info=True)

    await db.commit()

    return ThreatResponseResult(
        action=body.action,
        status="triggered",
        threat_id=body.threat_id,
        triggered_at=now.isoformat(),
        message=messages.get(body.action, "Action executed"),
    )


@router.post("/bulk", response_model=dict)
async def bulk_threat_action(
    body: BulkThreatAction,
    db: AsyncSession = Depends(get_db),
    claims: TokenClaims = Depends(require_permissions("vision:write")),
):
    now = datetime.now(timezone.utc)
    updated = 0

    for threat_id in body.threat_ids:
        result = await db.execute(
            select(ThreatDetection).where(
                ThreatDetection.id == threat_id,
                ThreatDetection.tenant_id == claims.tenant_id,
            )
        )
        threat = result.scalar_one_or_none()
        if not threat:
            continue

        if body.action == "acknowledge":
            threat.status = "acknowledged"
            threat.acknowledged_by = claims.user_id
            threat.acknowledged_at = now
        elif body.action == "resolve":
            threat.status = "resolved"
            threat.resolved_at = now
        elif body.action == "false_positive":
            threat.status = "false_positive"
            threat.resolved_at = now
        elif body.action == "escalate":
            threat.status = "investigating"
            if threat.severity in ("low", "medium"):
                threat.severity = "high"

        updated += 1

    await db.commit()
    return {"action": body.action, "updated": updated, "total": len(body.threat_ids)}


@router.get("/protocols")
async def get_response_protocols(
    claims: TokenClaims = Depends(require_permissions("vision:read")),
):
    """Return available response protocols for the SOC operator UI."""
    return {
        "protocols": [
            {
                "id": "lockdown",
                "name": "Zone Lockdown",
                "description": "Lock all entry/exit points in the specified zone",
                "severity_required": "high",
                "icon": "lock",
                "color": "red",
                "confirmation_required": True,
            },
            {
                "id": "dispatch_security",
                "name": "Dispatch Security",
                "description": "Send nearest security team to threat location",
                "severity_required": "medium",
                "icon": "shield",
                "color": "blue",
                "confirmation_required": False,
            },
            {
                "id": "notify_police",
                "name": "Notify PNP",
                "description": "Alert Philippine National Police via emergency channel",
                "severity_required": "critical",
                "icon": "phone",
                "color": "red",
                "confirmation_required": True,
            },
            {
                "id": "sound_alarm",
                "name": "Sound Alarm",
                "description": "Activate site-wide audible alarm",
                "severity_required": "high",
                "icon": "bell",
                "color": "orange",
                "confirmation_required": True,
            },
            {
                "id": "evacuate",
                "name": "Evacuation",
                "description": "Issue evacuation order for the affected zone",
                "severity_required": "critical",
                "icon": "log-out",
                "color": "red",
                "confirmation_required": True,
            },
            {
                "id": "isolate_zone",
                "name": "Isolate Zone",
                "description": "Restrict access to the specified zone",
                "severity_required": "medium",
                "icon": "slash",
                "color": "yellow",
                "confirmation_required": False,
            },
            {
                "id": "notify_management",
                "name": "Notify Management",
                "description": "Send SMS/Email alert to management team",
                "severity_required": "medium",
                "icon": "mail",
                "color": "blue",
                "confirmation_required": False,
            },
            {
                "id": "all_clear",
                "name": "All Clear",
                "description": "Signal threat neutralized — stand down response",
                "severity_required": "low",
                "icon": "check-circle",
                "color": "green",
                "confirmation_required": True,
            },
        ]
    }
