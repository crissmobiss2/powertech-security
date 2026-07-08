"""
Celery tasks for async processing.
All tasks use a synchronous DB session (celery runs in a sync context).
"""
import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.run(coro)


@celery_app.task(name="app.workers.tasks.process_security_event", bind=True, max_retries=3)
def process_security_event(self, event_id: str):
    """
    Process a security event:
    1. Index into Elasticsearch
    2. Evaluate matching playbooks
    3. Execute triggered playbooks
    """
    async def _process():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import settings
        from app.core.dependencies import TokenClaims
        from app.models.event import SecurityEvent
        from sqlalchemy import select

        engine = create_async_engine(settings.DATABASE_URL)
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

        async with SessionLocal() as db:
            result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == event_id))  # type: ignore
            event = result.scalar_one_or_none()
            if not event or event.processed:
                return

            # Build a system-level claims object for automated actions
            claims = TokenClaims(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),  # system user
                tenant_id=event.tenant_id,
                client_id=event.client_id,
                role="super_admin",
                permissions=["*"],
            )

            from app.services.automation_service import AutomationService
            svc = AutomationService(db, claims)
            try:
                executions = await svc.evaluate_event(event_id)
                logger.info("Event %s triggered %d playbook(s)", event_id, len(executions))
                await db.commit()
            except Exception as exc:
                await db.rollback()
                logger.exception("Failed to process event %s: %s", event_id, exc)
                raise self.retry(exc=exc, countdown=60)

        await engine.dispose()

    _run_async(_process())


@celery_app.task(name="app.workers.tasks.dispatch_alert", bind=True, max_retries=3)
def dispatch_alert(self, alert_id: str):
    """
    Dispatch an alert to all recipients across configured channels.
    Updates AlertRecipient.status for each delivery attempt.
    """
    async def _dispatch():
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from sqlalchemy import select
        from app.core.config import settings
        from app.models import Alert, User
        from app.models.alert import AlertRecipient
        from app.services.notification_service import NotificationService

        engine = create_async_engine(settings.DATABASE_URL)
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

        async with SessionLocal() as db:
            result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = result.scalar_one_or_none()
            if not alert or alert.status not in ("sending",):
                return

            recipients_result = await db.execute(
                select(AlertRecipient, User)
                .join(User, AlertRecipient.user_id == User.id)
                .where(AlertRecipient.alert_id == alert_id, AlertRecipient.status == "queued")
            )
            rows = recipients_result.all()

            svc = NotificationService()
            sent = failed = 0

            for recipient, user in rows:
                try:
                    result_data = {}
                    if recipient.channel == "sms" and user.phone:
                        result_data = await svc.send_sms(user.phone, alert.message)
                    elif recipient.channel == "email" and user.email:
                        result_data = await svc.send_email(
                            user.email,
                            alert.title,
                            f"<p>{alert.message}</p>",
                            alert.message,
                        )
                    elif recipient.channel == "whatsapp" and user.phone:
                        result_data = await svc.send_whatsapp(user.phone, alert.message)
                    else:
                        result_data = {"status": "skipped", "reason": "no_contact"}

                    status = result_data.get("status", "failed")
                    recipient.status = status if status in ("sent", "delivered") else "failed"
                    recipient.external_id = result_data.get("external_id")
                    recipient.sent_at = datetime.now(timezone.utc)
                    if recipient.status == "sent":
                        sent += 1
                    else:
                        failed += 1
                except Exception as exc:
                    logger.error("Alert dispatch failed for recipient %s: %s", recipient.id, exc)
                    recipient.status = "failed"
                    recipient.error_message = str(exc)[:500]
                    failed += 1

            alert.sent_count = sent
            alert.failed_count = failed
            alert.status = "sent" if failed == 0 else ("partial_failure" if sent > 0 else "failed")
            alert.sent_at = datetime.now(timezone.utc)
            await db.commit()

        await engine.dispose()

    _run_async(_dispatch())


@celery_app.task(name="app.workers.tasks.execute_playbook_async")
def execute_playbook_async(execution_id: str):
    """Continue async execution of a manually triggered playbook."""
    logger.info("Async playbook execution not yet implemented for execution %s", execution_id)


@celery_app.task(name="app.workers.tasks.sweep_asset_health")
def sweep_asset_health():
    """Periodic sweep: mark assets offline if no heartbeat received in threshold window."""
    logger.info("Asset health sweep started")
    # Implementation: query assets where last_seen_at < now() - threshold
    # and status != 'offline', update to 'offline', emit asset.offline event


@celery_app.task(name="app.workers.tasks.check_sla_breaches")
def check_sla_breaches():
    """Check for incidents and tickets past their SLA due date and notify."""
    logger.info("SLA breach check started")
    # Implementation: find incidents where sla_due_at < now() and status not in (resolved, closed)
    # create escalation timeline entries and alert escalated_to user
