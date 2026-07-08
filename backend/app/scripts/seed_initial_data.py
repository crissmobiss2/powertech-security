"""
Seed script: creates the initial Power Tech Security tenant + super_admin user.
Run once after initial migration:
  docker compose exec backend python -m app.scripts.seed_initial_data
"""
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import select
        result = await db.execute(select(Tenant).where(Tenant.slug == "powertech"))
        if result.scalar_one_or_none():
            print("Already seeded. Skipping.")
            return

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
        await db.commit()

        print(f"Tenant created: {tenant.id}")
        print(f"Admin user: {admin.email} (password: ChangeMe@2026!)")
        print("IMPORTANT: Change the default password immediately.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
