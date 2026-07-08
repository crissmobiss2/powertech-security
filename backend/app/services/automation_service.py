"""SOAR automation engine: evaluates playbooks and executes actions."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import TokenClaims
from app.models import Asset, Incident, Playbook, Site
from app.models.playbook import PlaybookExecution
from app.schemas.incident import IncidentCreate
from app.schemas.alert import AlertCreate
from app.schemas.ticket import TicketCreate


class AutomationService:
    def __init__(self, db: AsyncSession, claims: TokenClaims):
        self.db = db
        self.claims = claims

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def evaluate_event(self, event_id: str) -> list[PlaybookExecution]:
        """Find all matching playbooks for a security event and execute them."""
        from app.models.event import SecurityEvent
        result = await self.db.execute(
            select(SecurityEvent).where(SecurityEvent.id == event_id)  # type: ignore[arg-type]
        )
        event = result.scalar_one_or_none()
        if not event:
            return []

        pb_result = await self.db.execute(
            select(Playbook).where(
                Playbook.tenant_id == event.tenant_id,
                Playbook.enabled == True,
                Playbook.trigger_type == self._map_event_to_trigger(event.event_type),
            )
        )
        playbooks = pb_result.scalars().all()

        executions = []
        for pb in playbooks:
            if await self._conditions_match(pb, event):
                exec_result = await self._run_playbook(pb, event)
                if exec_result:
                    executions.append(exec_result)

        # Mark event as processed
        event.processed = True
        await self.db.flush()
        return executions

    def _map_event_to_trigger(self, event_type: str) -> str:
        mapping = {
            "asset.offline": "asset_offline",
            "asset.online": "asset_online",
            "incident.created": "incident_created",
        }
        for key, trigger in mapping.items():
            if event_type.startswith(key.split(".")[0]):
                return mapping.get(event_type, "webhook")
        return "webhook"

    async def _conditions_match(self, playbook: Playbook, event) -> bool:
        """Evaluate playbook conditions against the event context."""
        if not playbook.conditions:
            return True

        trigger_config = playbook.trigger_config or {}

        # asset_type filter
        if event.asset_id and "asset_types" in trigger_config:
            asset_result = await self.db.execute(
                select(Asset).where(Asset.id == event.asset_id)
            )
            asset = asset_result.scalar_one_or_none()
            if asset and asset.type not in trigger_config["asset_types"]:
                return False

        # site risk level filter
        if event.site_id and "site_risk_levels" in trigger_config:
            site_result = await self.db.execute(
                select(Site).where(Site.id == event.site_id)
            )
            site = site_result.scalar_one_or_none()
            if site and site.risk_level not in trigger_config["site_risk_levels"]:
                return False

        return True

    async def _run_playbook(self, playbook: Playbook, trigger_event) -> PlaybookExecution | None:
        """Execute all actions defined in the playbook sequentially."""
        execution = PlaybookExecution(
            playbook_id=playbook.id,
            tenant_id=self.claims.tenant_id,
            trigger_event={
                "event_id": str(trigger_event.id),
                "event_type": trigger_event.event_type,
                "asset_id": str(trigger_event.asset_id) if trigger_event.asset_id else None,
                "site_id": str(trigger_event.site_id) if trigger_event.site_id else None,
                "client_id": str(trigger_event.client_id),
            },
            status="running",
            started_at=self._now(),
        )
        self.db.add(execution)
        await self.db.flush()

        steps_completed = []
        context: dict = {"event": trigger_event, "execution_id": str(execution.id)}
        incident_id: UUID | None = None

        try:
            for i, action in enumerate(playbook.actions):
                action_type = action.get("type")
                action_config = action.get("config", {})

                if action_type == "create_incident":
                    incident = await self._action_create_incident(trigger_event, action_config)
                    incident_id = incident.id
                    execution.incident_id = incident_id
                    context["incident_id"] = str(incident_id)
                    steps_completed.append({"step": i, "type": action_type, "result": str(incident_id)})

                elif action_type == "send_alert":
                    alert_id = await self._action_send_alert(trigger_event, action_config, incident_id)
                    steps_completed.append({"step": i, "type": action_type, "result": str(alert_id)})

                elif action_type == "create_ticket":
                    ticket_id = await self._action_create_ticket(trigger_event, action_config, incident_id)
                    steps_completed.append({"step": i, "type": action_type, "result": str(ticket_id)})

            execution.status = "completed"
            execution.completed_at = self._now()
            execution.steps_completed = steps_completed

            # Update playbook stats
            playbook.run_count += 1
            playbook.last_triggered_at = self._now()

        except Exception as exc:
            execution.status = "failed"
            execution.completed_at = self._now()
            execution.error_message = str(exc)

        await self.db.flush()
        return execution

    async def _action_create_incident(self, event, config: dict) -> Incident:
        from app.services.incident_service import IncidentService

        # Determine title from event context
        asset_name = "Unknown Asset"
        if event.asset_id:
            asset_result = await self.db.execute(select(Asset).where(Asset.id == event.asset_id))
            asset = asset_result.scalar_one_or_none()
            if asset:
                asset_name = asset.name

        svc = IncidentService(self.db, self.claims)
        return await svc.create(IncidentCreate(
            client_id=event.client_id,
            site_id=event.site_id,
            title=config.get("title", f"Auto: {event.event_type} — {asset_name}"),
            description=config.get("description", f"Automated incident from event: {event.event_type}"),
            severity=config.get("severity", event.severity),
            type=config.get("type", "physical"),
            source="automated",
            metadata={"trigger_event_id": str(event.id), "playbook": "auto"},
        ))

    async def _action_send_alert(self, event, config: dict, incident_id: UUID | None) -> UUID:
        from app.services.alert_service import AlertService

        svc = AlertService(self.db, self.claims)
        alert = await svc.create_and_dispatch(AlertCreate(
            client_id=event.client_id,
            incident_id=incident_id,
            title=config.get("title", f"Security Alert: {event.event_type}"),
            message=config.get("message", f"Automated alert triggered for event: {event.event_type}"),
            severity=config.get("severity", event.severity),
            type="security",
            channels=config.get("channels", ["sms", "in_app"]),
            recipient_roles=config.get("roles", ["site_supervisor", "client_admin"]),
        ))
        return alert.id

    async def _action_create_ticket(self, event, config: dict, incident_id: UUID | None) -> UUID:
        from app.models.ticket import Ticket as TicketModel

        ticket = TicketModel(
            tenant_id=self.claims.tenant_id,
            client_id=event.client_id,
            site_id=event.site_id,
            incident_id=incident_id,
            asset_id=event.asset_id,
            title=config.get("title", f"Auto: Investigate {event.event_type}"),
            description=config.get("description", f"Automated ticket from playbook execution."),
            type=config.get("type", "support"),
            priority=config.get("priority", "high"),
            created_by=self.claims.user_id,
        )
        self.db.add(ticket)
        await self.db.flush()
        return ticket.id

    async def execute_playbook(
        self,
        playbook_id: UUID,
        trigger_event: dict | None,
        incident_id: UUID | None,
    ) -> PlaybookExecution:
        """Manual playbook execution."""
        result = await self.db.execute(
            select(Playbook).where(Playbook.id == playbook_id, Playbook.tenant_id == self.claims.tenant_id)
        )
        pb = result.scalar_one_or_none()
        if not pb:
            raise HTTPException(status_code=404, detail="Playbook not found")

        execution = PlaybookExecution(
            playbook_id=pb.id,
            tenant_id=self.claims.tenant_id,
            incident_id=incident_id,
            trigger_event=trigger_event or {"manual": True},
            status="running",
            started_at=self._now(),
        )
        self.db.add(execution)
        await self.db.flush()

        from app.workers.tasks import execute_playbook_async
        execute_playbook_async.delay(str(execution.id))

        await self.db.refresh(execution)
        return execution
