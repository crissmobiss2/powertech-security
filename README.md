# Power Tech Security Platform

Multi-tenant security operations platform unifying physical security, cybersecurity, and automation for Power Tech Security Corp (Philippines).

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your database password, secret key, etc.

# 2. Start all services
docker compose up -d

# 3. Run database migrations
docker compose exec backend alembic upgrade head

# 4. Seed initial data (creates admin@powertech.ph)
docker compose exec backend python -m app.scripts.seed_initial_data

# 5. Access
#   Frontend:  http://localhost:3000
#   API docs:  http://localhost:8000/docs
#   Celery UI: http://localhost:5555
```

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design document.

### Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.12), SQLAlchemy 2.0 async |
| Primary DB | PostgreSQL 16 |
| Cache / Queue | Redis 7 |
| Event Store | Elasticsearch 8 |
| Task Queue | Celery + Redis |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Containers | Docker + Docker Compose |

## Project Structure

```
powertech-security/
├── ARCHITECTURE.md          # Design document
├── docker-compose.yml       # All services
├── backend/
│   ├── app/
│   │   ├── core/           # Config, DB, security, dependencies
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── api/v1/         # REST endpoints
│   │   ├── services/       # Business logic
│   │   └── workers/        # Celery tasks
│   ├── alembic/            # DB migrations
│   └── scripts/            # Seed data
└── frontend/
    └── src/
        ├── app/            # Next.js App Router pages
        ├── components/     # React components
        ├── lib/            # API client, auth, utils
        └── types/          # TypeScript types
```

## End-to-End Flow: CCTV Offline Alert

1. **Event ingested** → `POST /api/v1/events/ingest` (from NVR integration)
2. **Celery worker** picks up event, evaluates playbooks
3. **Matching playbook** (CCTV Offline – High Risk Site) executes:
   - Creates Incident (severity: HIGH)
   - Sends Alert to site_supervisor + client_admin (SMS + in-app)
   - Creates Ticket assigned to IT support team
4. **Site supervisor** acknowledges alert
5. **Engineer** accepts ticket, checks in on-site, resolves issue
6. **SOC analyst** closes incident with resolution summary
7. Compliance report auto-generated

## Default Users (after seed)

| Email | Password | Role |
|---|---|---|
| admin@powertech.ph | ChangeMe@2026! | super_admin |

**Change passwords immediately after first login.**

## Development

```bash
# Backend only
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend only
cd frontend
npm install
npm run dev

# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

## Regulatory Compliance

This platform is designed to support:
- **RA 11917** (Private Security Services Industry Act)
- **PNP-SOSIA** inspection requirements
- **RA 10173** (Data Privacy Act) — audit trails, breach notification
- **DICT Cybersecurity Framework** — incident response, SIEM

See ARCHITECTURE.md §12 for details.
