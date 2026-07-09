"""
Seed script: creates the initial Power Tech Security tenant + super_admin user.
Run once after initial migration:
  docker compose exec backend python -m app.scripts.seed_initial_data
"""
import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User

log = logging.getLogger(__name__)


async def seed():
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

        async with SessionLocal() as db:
            from sqlalchemy import select

            # Upsert tenant
            result = await db.execute(select(Tenant).where(Tenant.slug == "powertech"))
            tenant = result.scalar_one_or_none()
            if tenant:
                log.info("Seed: tenant already exists id=%s", tenant.id)
            else:
                tenant = Tenant(
                    id=uuid.uuid4(),
                    name="Power Tech Security Corp",
                    slug="powertech",
                    subscription_tier="enterprise",
                    is_active=True,
                    settings={
                        "timezone": "Asia/Manila",
                        "currency": "PHP",
                        "country": "PH",
                    },
                )
                db.add(tenant)
                await db.flush()
                log.info("Seed: tenant created id=%s", tenant.id)

            # Upsert admin user
            user_result = await db.execute(
                select(User).where(User.email == "admin@powertech.ph", User.tenant_id == tenant.id)
            )
            admin = user_result.scalar_one_or_none()
            if admin:
                log.info("Seed: admin user already exists email=%s", admin.email)
            else:
                admin = User(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    email="admin@powertech.ph",
                    password_hash=hash_password("ChangeMe@2026!"),
                    first_name="System",
                    last_name="Administrator",
                    role="super_admin",
                    status="active",
                )
                db.add(admin)
                log.info("Seed: admin user created email=%s", admin.email)

            await db.commit()

        await engine.dispose()
    except Exception:
        log.exception("Seed failed")


if __name__ == "__main__":
    asyncio.run(seed())
