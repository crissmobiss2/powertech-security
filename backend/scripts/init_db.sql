-- Initial database setup script
-- Creates the database and extensions needed by the platform

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for column-level encryption (Phase 2)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Seed initial Power Tech Security tenant and super_admin user
-- Run AFTER alembic migrations: docker compose exec backend alembic upgrade head
-- Then: docker compose exec backend python -m app.scripts.seed_initial_data
