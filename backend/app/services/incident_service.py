"""Incident business logic: create, update, acknowledge, close, SLA tracking."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import TokenClaims
from app.models import Client, Incident
from app.models.incident import IncidentTimeline
from app.schemas.incident import IncidentCloseRequest, IncidentCreate, IncidentUpdate

SEVERITY_SLA_HOURS = {
    "critical": 1,
    "high": 4,
    "medium": 24,
    "low": 72,
    "info": 168,
}


class IncidentService:
    def __init__(self, db: AsyncSession, claims: TokenClaims):
        self.db = db
        self.claims = claims

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def _get_client_sla(self, client_id: UUID) -> dict:
        result = await self.db.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if client and client.sla_config:
            return client.sla_config
        return {}

    def _compute_sla(self, severity: str, client_sla: dict) -> datetime:
        default_hours = SEVERITY_SLA_HOURS.get(severity, 24)
        field_map = {
            "critical": "critical_response_hours",
            "high": "high_response_hours",
            "medium": "medium_response_hours",
            "low": "low_response_hours",
        }
        hours = client_sla.get(field_map.get(severity, ""), default_hours)
        return self._now() + timedelta(hours=float(hours))

    async def _add_timeline(self, incident_id: UUID, event_type: str, description: str, metadata: dict | None = None):
        entry = IncidentTimeline(
            incident_id=incident_id,
            tenant_id=self.claims.tenant_id,
            user_id=self.claims.user_id,
            event_type=event_type,
            description=description,
            metadata=metadata,
            created_at=self._now(),
        )
        self.db.add(entry)

    async def create(self, body: IncidentCreate) -> Incident:
        client_sla = await self._get_client_sla(body.client_id)
        sla_due_at = self._compute_sla(body.severity, client_sla)

        incident = Incident(
            tenant_id=self.claims.tenant_id,
            created_by=self.claims.user_id,
            sla_due_at=sla_due_at,
            **body.model_dump(),
        )
        self.db.add(incident)
        await self.db.flush()

        await self._add_timeline(
            incident.id,
            "created",
            f"Incident created by {self.claims.user_id}",
            {"severity": body.severity, "type": body.type, "source": body.source},
        )
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def update(self, incident_id: UUID, body: IncidentUpdate) -> Incident:
        result = await self.db.execute(
            select(Incident).where(
                Incident.id == incident_id,
                Incident.tenant_id == self.claims.tenant_id,
            )
        )
        incident = result.scalar_one_or_none()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        changes = body.model_dump(exclude_none=True)
        old_severity = incident.severity
        old_status = incident.status

        for field, value in changes.items():
            setattr(incident, field, value)

        if "severity" in changes and changes["severity"] != old_severity:
            await self._add_timeline(
                incident.id, "severity_changed",
                f"Severity changed from {old_severity} to {changes['severity']}",
            )
        if "status" in changes and changes["status"] != old_status:
            await self._add_timeline(
                incident.id, "status_changed",
                f"Status changed from {old_status} to {changes['status']}",
            )
        if "assigned_to" in changes:
            await self._add_timeline(
                incident.id, "assigned",
                f"Assigned to user {changes['assigned_to']}",
            )

        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def acknowledge(self, incident_id: UUID) -> Incident:
        result = await self.db.execute(
            select(Incident).where(Incident.id == incident_id, Incident.tenant_id == self.claims.tenant_id)
        )
        incident = result.scalar_one_or_none()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
        if incident.acknowledged_at:
            return incident
        incident.acknowledged_at = self._now()
        incident.status = "acknowledged"
        await self._add_timeline(incident.id, "acknowledged", "Incident acknowledged")
        await self.db.flush()
        await self.db.refresh(incident)
        return incident

    async def close(self, incident_id: UUID, body: IncidentCloseRequest) -> Incident:
        result = await self.db.execute(
            select(Incident).where(Incident.id == incident_id, Incident.tenant_id == self.claims.tenant_id)
        )
        incident = result.scalar_one_or_none()
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        incident.status = body.status
        incident.resolution_summary = body.resolution_summary
        incident.closed_at = self._now()
        if not incident.resolved_at:
            incident.resolved_at = self._now()

        await self._add_timeline(
            incident.id,
            "closed",
            f"Incident closed: {body.status}. Summary: {body.resolution_summary[:100]}",
        )
        await self.db.flush()
        await self.db.refresh(incident)
        return incident
