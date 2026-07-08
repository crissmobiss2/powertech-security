"""Alert creation and dispatch service."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import TokenClaims
from app.models import Alert, User
from app.models.alert import AlertRecipient
from app.schemas.alert import AlertCreate


class AlertService:
    def __init__(self, db: AsyncSession, claims: TokenClaims):
        self.db = db
        self.claims = claims

    async def _resolve_recipients(
        self,
        user_ids: list[UUID] | None,
        roles: list[str] | None,
        client_id: UUID | None,
    ) -> list[User]:
        q = select(User).where(
            User.tenant_id == self.claims.tenant_id,
            User.status == "active",
            User.deleted_at.is_(None),
        )
        if client_id:
            q = q.where(User.client_id == client_id)
        if roles:
            q = q.where(User.role.in_(roles))

        result = await self.db.execute(q)
        users = list(result.scalars().all())

        if user_ids:
            id_result = await self.db.execute(
                select(User).where(User.id.in_(user_ids), User.tenant_id == self.claims.tenant_id)
            )
            extra = id_result.scalars().all()
            existing_ids = {u.id for u in users}
            users.extend(u for u in extra if u.id not in existing_ids)

        return users

    async def create_and_dispatch(self, body: AlertCreate) -> Alert:
        recipients = await self._resolve_recipients(
            body.recipient_user_ids,
            body.recipient_roles,
            body.client_id,
        )

        alert = Alert(
            tenant_id=self.claims.tenant_id,
            client_id=body.client_id,
            incident_id=body.incident_id,
            title=body.title,
            message=body.message,
            severity=body.severity,
            type=body.type,
            channels=body.channels,
            total_recipients=len(recipients),
            status="sending",
            scheduled_at=body.scheduled_at,
            created_by=self.claims.user_id,
        )
        self.db.add(alert)
        await self.db.flush()

        # Create recipient entries for each user × channel combination
        for user in recipients:
            for channel in body.channels:
                recipient = AlertRecipient(
                    alert_id=alert.id,
                    user_id=user.id,
                    channel=channel,
                    status="queued",
                )
                self.db.add(recipient)

        await self.db.flush()

        # Queue dispatch tasks
        from app.workers.tasks import dispatch_alert
        dispatch_alert.delay(str(alert.id))

        await self.db.refresh(alert)
        return alert

    async def dispatch_existing(self, alert: Alert) -> Alert:
        """Re-dispatch a failed alert."""
        alert.status = "sending"
        await self.db.flush()
        from app.workers.tasks import dispatch_alert
        dispatch_alert.delay(str(alert.id))
        await self.db.refresh(alert)
        return alert
