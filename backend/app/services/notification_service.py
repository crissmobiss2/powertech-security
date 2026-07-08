"""Multi-channel notification dispatch: SMS, email, push, in-app."""
import logging
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles actual delivery to external channels. Called from Celery workers."""

    async def send_sms(self, phone: str, message: str, external_id: str | None = None) -> dict:
        """Send SMS via Infobip."""
        if not settings.SMS_API_KEY:
            logger.warning("SMS not configured — skipping for %s", phone)
            return {"status": "skipped", "reason": "not_configured"}

        payload = {
            "messages": [{
                "from": settings.SMS_SENDER,
                "destinations": [{"to": phone}],
                "text": message,
            }]
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.SMS_BASE_URL}/sms/2/text/advanced",
                json=payload,
                headers={
                    "Authorization": f"App {settings.SMS_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
        resp.raise_for_status()
        data = resp.json()
        msg_result = data.get("messages", [{}])[0]
        return {
            "external_id": msg_result.get("messageId"),
            "status": "sent" if msg_result.get("status", {}).get("groupName") in ("PENDING", "DELIVERED") else "failed",
        }

    async def send_email(
        self, to_email: str, subject: str, body_html: str, body_text: str = ""
    ) -> dict:
        """Send email via SMTP (aiosmtplib)."""
        if not settings.SMTP_HOST:
            logger.warning("Email not configured — skipping for %s", to_email)
            return {"status": "skipped", "reason": "not_configured"}
        try:
            import aiosmtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            msg["To"] = to_email
            if body_text:
                msg.attach(MIMEText(body_text, "plain"))
            msg.attach(MIMEText(body_html, "html"))

            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_PORT == 465,
                start_tls=settings.SMTP_PORT == 587,
            )
            return {"status": "sent"}
        except Exception as e:
            logger.error("Email send failed to %s: %s", to_email, e)
            return {"status": "failed", "error": str(e)}

    async def send_whatsapp(self, phone: str, message: str) -> dict:
        """Send WhatsApp message via WhatsApp Business API."""
        if not settings.WHATSAPP_TOKEN:
            return {"status": "skipped", "reason": "not_configured"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": message},
                },
                headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
                timeout=10,
            )
        resp.raise_for_status()
        return {"status": "sent", "external_id": resp.json().get("messages", [{}])[0].get("id")}

    async def send_push(self, fcm_token: str, title: str, body: str, data: dict | None = None) -> dict:
        """Send push notification via Firebase FCM."""
        if not settings.FIREBASE_PROJECT_ID:
            return {"status": "skipped", "reason": "not_configured"}
        try:
            from firebase_admin import messaging
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                token=fcm_token,
            )
            response = messaging.send(message)
            return {"status": "sent", "external_id": response}
        except Exception as e:
            logger.error("Push notification failed: %s", e)
            return {"status": "failed", "error": str(e)}
