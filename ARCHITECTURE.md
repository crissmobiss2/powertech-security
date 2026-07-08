# Power Tech Security Platform — Architecture Document
**Version:** 1.0 | **Date:** 2026-07-08 | **Status:** Active

---

## 1. Executive Summary

Power Tech Security is a multi-tenant SaaS platform unifying **physical security operations** (CCTV, access control, installations) with **cybersecurity operations** (SOC, SIEM, vulnerability management) and **security automation** (SOAR across physical and cyber domains) under a single pane of glass.

The platform serves Power Tech Security Corp (Philippines) as the operator, managing multiple enterprise clients, each with their own sites, assets, personnel, and security posture.

---

## 2. Business Context & Regulatory Framework

### 2.1 Philippine Regulatory Alignment

| Regulation | Requirement | Platform Support |
|---|---|---|
| **RA 11917** (Private Security Services Industry Act) | Licensing, MDR, DDO records, firearm logs, guard training | Reporting module, audit trail, compliance dashboards |
| **PNP-SOSIA** | Monthly Detail Reports, deployment records, inspector access | Role-scoped reporting, read-only auditor role |
| **RA 10173** (Data Privacy Act) | Personal data protection, breach notification | Encryption at rest/transit, DPA incident workflow |
| **BSP Circular 982** (for financial clients) | Cybersecurity framework | SOC module, vulnerability SLAs, audit logs |

### 2.2 Business Lines in Scope

1. **Security Hardware & System Solutions** ← Primary focus of this build
2. Security Agency Operations (PSA/CGF) ← Phase 2 extension
3. Executive & VIP Protection ← Phase 3 extension

---

## 3. Domain Model & Bounded Contexts

### 3.1 Bounded Contexts

```
┌─────────────────────────────────────────────────────────────────┐
│                    POWER TECH SECURITY PLATFORM                  │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  PHYSICAL DOMAIN │  │   CYBER DOMAIN   │  │ AUTOMATION DOM. │ │
│  │                 │  │                 │  │                 │ │
│  │ CCTV Mgmt       │  │ SOC / SIEM      │  │ SOAR Engine     │ │
│  │ Access Control  │  │ Vulnerability   │  │ Playbooks       │ │
│  │ Installations   │  │ Network Sec     │  │ Workflows       │ │
│  │ Field Service   │  │ Forensics       │  │ AI Suggestions  │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │           │
│  ┌────────▼────────────────────▼────────────────────▼────────┐  │
│  │              SHARED KERNEL                                 │  │
│  │  Client · Site · Asset · Incident · Alert · User · Audit  │  │
│  └─────────────────────────────────────────────────────────── │  │
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │  NOTIFICATIONS  │  │   COMPLIANCE    │                       │
│  │ SMS/Email/Push  │  │ Reports/Audit   │                       │
│  │ Emergency Alert │  │ Regulatory Docs │                       │
│  └─────────────────┘  └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Core Entities by Domain

**Shared Kernel:**
`Tenant` → `Client` → `Site` → `Asset` → `Incident` → `Alert`

**Physical Domain:**
`InstallationProject` · `WorkOrder` · `Ticket` · `EquipmentRegistry`

**Cyber Domain:**
`SecurityEvent` · `Vulnerability` · `Forensic Case` · `Evidence`

**Automation:**
`Playbook` · `PlaybookExecution` · `Rule` · `Action`

---

## 4. System Architecture

### 4.1 High-Level Architecture

```
                         ┌───────────────────┐
                         │   CDN / WAF        │
                         │  (Cloudflare)      │
                         └────────┬──────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼──────┐  ┌────────▼───────┐  ┌───────▼────────┐
    │  Next.js Web   │  │  Mobile App    │  │  External APIs  │
    │  (React)       │  │  (React Native)│  │  Integrations   │
    └─────────┬──────┘  └────────┬───────┘  └───────┬────────┘
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
                        ┌─────────▼─────────┐
                        │   API Gateway      │
                        │  (nginx / Kong)    │
                        └─────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼──────┐  ┌────────▼───────┐  ┌───────▼────────┐
    │  FastAPI Core  │  │  WebSocket Srv │  │  Auth Service   │
    │  (REST API)    │  │  (Real-time)   │  │  (JWT/OAuth2)   │
    └─────────┬──────┘  └────────┬───────┘  └───────┬────────┘
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼──────┐  ┌────────▼───────┐  ┌───────▼────────┐
    │  PostgreSQL     │  │  Redis          │  │ Elasticsearch  │
    │  (Core Data)   │  │  (Cache/PubSub) │  │ (Events/Logs)  │
    └────────────────┘  └────────────────┘  └────────────────┘
              │
    ┌─────────▼──────┐
    │  Celery Workers │
    │  (Async Tasks)  │
    └────────────────┘
```

### 4.2 Service Decomposition

Rather than microservices from day one, we use a **modular monolith** with clearly separated Python packages. Each module can be extracted as a microservice when scale demands it.

| Module Package | Responsibility |
|---|---|
| `app.domains.clients` | Client & site CRUD, contract management |
| `app.domains.assets` | Asset registry (CMDB), status, maintenance |
| `app.domains.incidents` | Incident lifecycle, triage, assignment |
| `app.domains.alerts` | Mass notification, delivery tracking |
| `app.domains.tickets` | Work orders, field service, SLA |
| `app.domains.security_events` | Event ingestion, correlation, SIEM |
| `app.domains.vulnerabilities` | Vuln management, remediation workflows |
| `app.domains.forensics` | Case management, evidence chain |
| `app.domains.automation` | Playbooks, SOAR engine, AI suggestions |
| `app.domains.compliance` | Reports, audit trails, regulatory docs |
| `app.domains.notifications` | Multi-channel notification engine |

### 4.3 Data Flow: Security Event Processing

```
Physical/Cyber Event Source
         │
         ▼
  Event Ingestion API ──── Validate & enrich
         │
         ▼
  Redis Queue (Celery)
         │
         ├──► Elasticsearch (raw log storage, searchable)
         │
         ├──► Correlation Engine
         │         │
         │         ├── Matches rule? ──► Create/update Incident
         │         │                         │
         │         │                         ▼
         │         │                   Playbook Engine
         │         │                         │
         │         │               ┌─────────┴─────────┐
         │         │               │                   │
         │         │          Notify Team         Create Ticket
         │         │               │
         │         │          Alert Service
         │         │         (SMS/Email/Push)
         │         │
         └── No match? ──► Store for review
```

---

## 5. Technology Stack

### 5.1 Decisions & Rationale

| Layer | Choice | Rationale |
|---|---|---|
| **Backend** | FastAPI (Python 3.12) | Async-first, excellent type hints, auto OpenAPI docs, huge security tooling ecosystem, AI/ML integration path |
| **ORM** | SQLAlchemy 2.0 (async) | Production-proven, async support, excellent migration tooling via Alembic |
| **Primary DB** | PostgreSQL 16 | JSONB for flexible metadata, row-level security for defense in depth, full-text search, mature ecosystem |
| **Cache / PubSub** | Redis 7 | Fast session store, real-time pub/sub for WebSockets, Celery broker |
| **Event Store** | Elasticsearch 8 | Full-text log search, time-series aggregations, Kibana dashboards for SOC analysts |
| **Task Queue** | Celery + Redis | Async notification dispatch, playbook execution, scheduled jobs |
| **Frontend** | Next.js 14 (App Router) | SSR for initial load performance, React ecosystem, excellent TypeScript support |
| **UI Components** | Tailwind CSS + shadcn/ui | No vendor lock-in, accessibility-first, composable |
| **Real-time** | WebSockets (FastAPI native) | Low-latency dashboard updates, alert delivery confirmations |
| **Auth** | JWT (access + refresh) | Stateless, multi-tenant capable, standard |
| **Container** | Docker + Docker Compose | Reproducible dev environment, easy production migration |

---

## 6. Data Model

### 6.1 Multi-Tenancy Strategy

**Approach:** Shared database, tenant-discriminated rows via `tenant_id` column.

- All tenant-scoped tables carry `tenant_id UUID NOT NULL`.
- FastAPI middleware extracts `tenant_id` from JWT and injects it into every query via dependency injection.
- PostgreSQL Row-Level Security (RLS) policies add defense-in-depth (applied in Phase 2).
- Elasticsearch uses index-per-tenant for log isolation.

**Tenant hierarchy:**
```
Tenant (Power Tech Security Corp)
  └── Client (e.g., "BDO Unibank")
        └── Site (e.g., "BDO Makati Head Office")
              └── Asset (e.g., "Camera CAM-001")
```

### 6.2 Entity Relationship Description

#### Core Entities

**tenants**
```
id UUID PK | name | slug | subscription_tier | settings JSONB
created_at | updated_at | is_active
```

**users**
```
id UUID PK | tenant_id FK | client_id FK(nullable) | email UNIQUE
password_hash | first_name | last_name | role ENUM | status ENUM
phone | avatar_url | last_login_at | mfa_enabled | mfa_secret
created_at | updated_at | deleted_at
INDEX: (tenant_id, email), (tenant_id, role)
```

**user_sessions** (refresh token store)
```
id UUID PK | user_id FK | token_hash | device_info JSONB
ip_address INET | expires_at | revoked_at | created_at
INDEX: (token_hash), (user_id)
```

**clients**
```
id UUID PK | tenant_id FK | code VARCHAR(20) UNIQUE | name
industry | risk_tier ENUM(critical/high/medium/low) | status ENUM
billing_email | address JSONB | sla_config JSONB
account_manager_id FK(users) | created_at | updated_at | deleted_at
INDEX: (tenant_id), (tenant_id, status), (code)
```

**sites**
```
id UUID PK | tenant_id FK | client_id FK | name | code
address JSONB | coordinates POINT | risk_level ENUM
timezone VARCHAR | type ENUM(office/datacenter/warehouse/retail/...)
floor_plans JSONB | emergency_contacts JSONB
created_at | updated_at | deleted_at
INDEX: (tenant_id, client_id), (tenant_id, risk_level)
```

**contacts**
```
id UUID PK | tenant_id FK | client_id FK | site_id FK(nullable)
name | role | email | phone | is_primary | created_at | updated_at
```

#### Asset Management

**assets**
```
id UUID PK | tenant_id FK | client_id FK | site_id FK
name | code VARCHAR(50) | type ENUM | sub_type VARCHAR
status ENUM(online/offline/degraded/maintenance/decommissioned/unknown)
ip_address INET | mac_address MACADDR | serial_number
manufacturer | model | firmware_version | purchase_date DATE
warranty_expires DATE | location_detail | floor | zone
last_seen_at | last_health_check_at | metadata JSONB
created_by FK(users) | created_at | updated_at | deleted_at
INDEX: (tenant_id, client_id), (tenant_id, type, status)
       (site_id), (serial_number), (ip_address)
```

**asset_tags** (many-to-many assets ↔ tags)
```
asset_id FK | tag VARCHAR | PRIMARY KEY(asset_id, tag)
```

**asset_maintenance_logs**
```
id UUID PK | asset_id FK | tenant_id FK | type ENUM
performed_by FK(users) | description | parts_used JSONB
cost NUMERIC | performed_at | next_maintenance_at | created_at
```

#### Incident Management

**incidents**
```
id UUID PK | tenant_id FK | client_id FK | site_id FK(nullable)
title | description TEXT | severity ENUM(critical/high/medium/low/info)
status ENUM(new/acknowledged/investigating/in_progress/resolved/closed/false_positive)
type ENUM(physical/cyber/combined/operational)
source ENUM(manual/automated/integration/alert)
assigned_to FK(users) | escalated_to FK(users)
sla_due_at | acknowledged_at | resolved_at | closed_at
resolution_summary TEXT | tags JSONB | metadata JSONB
parent_incident_id FK(self, nullable)
created_by FK(users) | created_at | updated_at
INDEX: (tenant_id, client_id, status), (tenant_id, severity, status)
       (assigned_to), (created_at DESC), (sla_due_at)
```

**incident_timeline**
```
id UUID PK | incident_id FK | tenant_id FK | user_id FK(nullable)
event_type ENUM | description | metadata JSONB | created_at
INDEX: (incident_id, created_at)
```

**incident_attachments**
```
id UUID PK | incident_id FK | tenant_id FK | filename | storage_path
file_type | file_size | uploaded_by FK(users) | created_at
```

#### Alert & Notification System

**alerts**
```
id UUID PK | tenant_id FK | client_id FK(nullable) | incident_id FK(nullable)
title | message TEXT | severity ENUM | type ENUM(security/operational/emergency/test)
status ENUM(draft/sending/sent/partial_failure/failed)
channels JSONB (array of: sms/email/push/voice/whatsapp/telegram/in_app)
total_recipients | sent_count | delivered_count | acknowledged_count | failed_count
scheduled_at | sent_at | created_by FK(users) | created_at | updated_at
INDEX: (tenant_id, status), (incident_id), (created_at DESC)
```

**alert_recipients**
```
id UUID PK | alert_id FK | user_id FK | channel ENUM
status ENUM(queued/sent/delivered/read/acknowledged/failed)
external_id VARCHAR | sent_at | delivered_at | read_at | acknowledged_at
error_message | metadata JSONB
INDEX: (alert_id), (user_id, status)
```

#### Work Orders & Field Service

**tickets**
```
id UUID PK | tenant_id FK | client_id FK | site_id FK(nullable)
incident_id FK(nullable) | asset_id FK(nullable)
title | description TEXT | type ENUM(installation/maintenance/support/investigation/emergency/inspection)
status ENUM(open/assigned/in_progress/on_hold/resolved/closed/cancelled)
priority ENUM(critical/high/medium/low)
assigned_to FK(users) | assigned_team JSONB
sla_due_at | checkin_at | checkout_at | resolved_at | closed_at
client_signoff_at | client_signoff_by
labor_hours NUMERIC | parts_used JSONB | cost NUMERIC
resolution_notes TEXT | client_notes TEXT
created_by FK(users) | created_at | updated_at
INDEX: (tenant_id, client_id, status), (assigned_to, status)
       (site_id), (incident_id), (sla_due_at)
```

**ticket_comments**
```
id UUID PK | ticket_id FK | user_id FK | content TEXT
is_internal BOOLEAN | attachments JSONB | created_at | updated_at
```

#### Security Automation (SOAR)

**playbooks**
```
id UUID PK | tenant_id FK | name | description TEXT
trigger_type ENUM(asset_offline/incident_created/incident_severity/scheduled/manual/webhook/threshold)
trigger_config JSONB | conditions JSONB (CEL expressions)
actions JSONB (ordered array of action definitions)
enabled BOOLEAN | run_count | last_triggered_at
created_by FK(users) | created_at | updated_at
INDEX: (tenant_id, enabled, trigger_type)
```

**playbook_executions**
```
id UUID PK | playbook_id FK | incident_id FK(nullable) | tenant_id FK
trigger_event JSONB | status ENUM(running/completed/failed/cancelled)
started_at | completed_at | error_message
steps_completed JSONB | results JSONB
```

#### Cybersecurity Domain

**security_events** (hot table — partition by month)
```
id UUID PK | tenant_id FK | client_id FK | site_id FK(nullable)
asset_id FK(nullable) | incident_id FK(nullable)
event_type VARCHAR | source_type VARCHAR | source_name VARCHAR
severity ENUM | raw_data JSONB | normalized_data JSONB
processed BOOLEAN | false_positive BOOLEAN | tags JSONB
created_at TIMESTAMPTZ (partition key)
INDEX: (tenant_id, client_id, created_at), (event_type, created_at)
       (asset_id, created_at), (processed, created_at)
```

**vulnerabilities**
```
id UUID PK | tenant_id FK | client_id FK | site_id FK(nullable)
asset_id FK(nullable) | cve_id VARCHAR | title | description TEXT
severity ENUM | cvss_score NUMERIC(4,2) | cvss_vector
status ENUM(open/in_remediation/resolved/accepted_risk/false_positive)
discovered_at | sla_due_at | remediated_at | verified_at
remediation_notes TEXT | affected_versions JSONB
scanner_source VARCHAR | scan_id VARCHAR
assigned_to FK(users) | created_at | updated_at
INDEX: (tenant_id, client_id, status), (asset_id, status)
       (severity, status), (cve_id)
```

**evidence_items** (forensics)
```
id UUID PK | tenant_id FK | incident_id FK | client_id FK
name | type ENUM(disk_image/memory_dump/log_file/screenshot/network_capture/document/other)
description TEXT | file_hash_sha256 | file_hash_md5
storage_path | file_size | collected_by FK(users) | collected_at
chain_of_custody JSONB (append-only array)
integrity_verified_at | tags JSONB | created_at | updated_at
```

**contracts**
```
id UUID PK | tenant_id FK | client_id FK
reference_number VARCHAR UNIQUE | service_type ENUM
start_date DATE | end_date DATE | auto_renew BOOLEAN
value NUMERIC | currency VARCHAR(3) DEFAULT 'PHP'
billing_cycle ENUM | payment_terms INTEGER
status ENUM(draft/active/suspended/expired/terminated)
services JSONB (included service modules) | sla_config JSONB
signed_at | created_by FK(users) | created_at | updated_at
INDEX: (tenant_id, client_id, status), (end_date)
```

**backup_jobs**
```
id UUID PK | tenant_id FK | client_id FK | asset_id FK(nullable)
job_name | type ENUM(full/incremental/differential/snapshot)
status ENUM(running/success/failed/missed/skipped)
started_at | completed_at | size_bytes BIGINT
rpo_hours NUMERIC | rto_hours NUMERIC | retention_days INTEGER
storage_location | checksum | verified BOOLEAN
incident_id FK(nullable) | created_at
INDEX: (tenant_id, client_id, status), (asset_id), (started_at DESC)
```

---

## 7. RBAC Model

### 7.1 Role Definitions

| Role | Scope | Key Permissions |
|---|---|---|
| `super_admin` | Platform | Full access: tenant management, billing, global config |
| `client_admin` | Client | Manage their client's users, view all modules for their client |
| `security_director` | Client | SOC oversight, approve playbooks, all incident access, compliance reports |
| `soc_analyst` | Client | Create/manage incidents, run playbooks, view SIEM, create alerts |
| `it_engineer` | Client | Manage assets, tickets, vulnerabilities, network module |
| `field_technician` | Client | Own tickets only, check-in/out, asset status updates |
| `site_supervisor` | Site | Incidents and alerts for assigned sites only |
| `executive` | Client | Read-only: dashboards, risk scores, key metrics |
| `auditor` | Client | Read-only: all data + compliance reports, audit trail access |

### 7.2 Permission Matrix (abbreviated)

| Permission | super_admin | client_admin | soc_analyst | it_engineer | field_tech |
|---|:---:|:---:|:---:|:---:|:---:|
| `clients:write` | ✓ | — | — | — | — |
| `incidents:create` | ✓ | ✓ | ✓ | ✓ | — |
| `incidents:close` | ✓ | ✓ | ✓ | — | — |
| `alerts:send` | ✓ | ✓ | ✓ | — | — |
| `playbooks:execute` | ✓ | ✓ | ✓ | — | — |
| `playbooks:create` | ✓ | ✓ | — | — | — |
| `assets:write` | ✓ | ✓ | — | ✓ | partial |
| `tickets:create` | ✓ | ✓ | ✓ | ✓ | — |
| `tickets:assign` | ✓ | ✓ | — | ✓ | — |
| `vulnerabilities:write` | ✓ | ✓ | ✓ | ✓ | — |
| `contracts:write` | ✓ | — | — | — | — |
| `users:manage` | ✓ | ✓ | — | — | — |
| `reports:compliance` | ✓ | ✓ | — | — | ✓(read) |

---

## 8. API Design

### 8.1 REST API Conventions

- **Base URL:** `https://api.powertech.ph/api/v1/`
- **Auth:** `Authorization: Bearer <access_token>`
- **Tenant:** Resolved from JWT claim `tenant_id`
- **Pagination:** `?page=1&limit=20&sort=created_at&order=desc`
- **Filtering:** `?status=active&severity=high&client_id=<uuid>`
- **Response envelope:**

```json
{
  "data": { ... } | [ ... ],
  "meta": { "total": 100, "page": 1, "limit": 20, "pages": 5 },
  "errors": null
}
```

- **Soft deletes:** `DELETE` sets `deleted_at`; `?include_deleted=true` to see them
- **Audit:** Every mutating endpoint auto-creates an audit log entry

### 8.2 WebSocket Events

```
ws://api.powertech.ph/ws?token=<access_token>

Subscriptions (client sends):
  { "action": "subscribe", "channel": "incidents:client:<client_id>" }
  { "action": "subscribe", "channel": "alerts:tenant" }
  { "action": "subscribe", "channel": "assets:site:<site_id>" }

Server pushes:
  { "event": "incident.created", "data": { ... } }
  { "event": "incident.status_changed", "data": { ... } }
  { "event": "asset.status_changed", "data": { ... } }
  { "event": "alert.sent", "data": { ... } }
```

---

## 9. End-to-End Example Flow: CCTV Offline Alert

```
1. CCTV camera at "BDO Makati HQ" site fails (no heartbeat for 5 min)
   │
   ▼
2. NVR integration or health check agent POSTs to:
   POST /api/v1/events/ingest
   { "type": "asset.offline", "asset_id": "cam-001", "site_id": "...", "client_id": "..." }
   │
   ▼
3. Event Processor (Celery task):
   - Stores raw event in Elasticsearch
   - Checks site risk_level = "HIGH"
   - Matches playbook: "CCTV Offline - High Risk Site Auto-Response"
   │
   ▼
4. Playbook Engine executes:
   Action 1: Create Incident (severity=HIGH, type=PHYSICAL)
     → Incident #INC-2026-001: "Camera CAM-001 Offline – BDO Makati HQ"
   Action 2: Send Alert to [site_supervisor, client_admin]
     → SMS to Maria Santos (Site Supervisor): "ALERT: Camera offline at BDO Makati..."
     → Email + in-app to Juan Cruz (Client Admin): same
   Action 3: Create Ticket assigned to IT Support team
     → Ticket #TKT-2026-001: "Investigate CCTV offline CAM-001"
   │
   ▼
5. Maria Santos acknowledges alert via SMS reply or mobile app
   → alert_recipient.status = "acknowledged"
   → incident_timeline entry: "Alert acknowledged by site supervisor"
   │
   ▼
6. IT Engineer Paolo Reyes is notified, accepts ticket, checks in on-site
   → ticket.status = "in_progress", ticket.checkin_at = now()
   → Finds cable damaged, replaces it, camera comes back online
   │
   ▼
7. Reconnection event received:
   POST /api/v1/events/ingest { "type": "asset.online", "asset_id": "cam-001" }
   │
   ▼
8. Paolo closes ticket with resolution notes, client signs off
   → ticket.status = "closed", ticket.client_signoff_at = now()
   │
   ▼
9. SOC Analyst closes incident with summary
   → incident.status = "closed", incident.resolution_summary = "..."
   │
   ▼
10. Compliance report generated:
    → Incident report with full timeline
    → SLA adherence metrics (was it resolved within SLA window?)
    → Alert delivery and acknowledgement audit
```

---

## 10. Integration Architecture

### 10.1 Physical Systems

| System | Integration Method | Direction |
|---|---|---|
| Hikvision NVR/DVS | REST API + ISAPI | Bidirectional |
| Dahua VMS | REST API | Bidirectional |
| ZKTeco Access Control | REST API + TCP Socket | Bidirectional |
| Suprema Biometrics | REST API | Inbound |
| Milestone XProtect | REST + Event API | Inbound |
| Generic ONVIF cameras | ONVIF WS-Discovery | Inbound |

### 10.2 Cyber Systems

| System | Integration Method |
|---|---|
| pfSense / OPNsense | Syslog + REST API |
| Fortinet FortiGate | FortiOS REST API + Syslog |
| Microsoft Defender EDR | Microsoft Graph API |
| Qualys / Nessus | REST API (scheduled scan import) |
| Microsoft Sentinel | REST API |
| Wazuh SIEM | REST API + agent integration |
| Cloudflare | Logpush + REST API |

### 10.3 Communication Channels

| Channel | Provider | Use Case |
|---|---|---|
| SMS | Globe / Smart Infobip | Emergency alerts, OTP |
| Voice Call | Twilio / Plivo | Critical alerts |
| Email | SendGrid / Postmark | Reports, standard alerts |
| Push Notification | Firebase FCM | Mobile app alerts |
| WhatsApp | WhatsApp Business API | Client communications |
| Telegram Bot | Telegram Bot API | SOC team alerts |

---

## 11. Security Architecture

- **Transport:** TLS 1.3 everywhere; HSTS enforced
- **Authentication:** JWT RS256 (asymmetric signing); access token 15 min, refresh 7 days
- **Secrets Management:** Environment variables; rotate via Vault (Phase 2)
- **Data at Rest:** PostgreSQL encryption; sensitive fields (PII) encrypted at column level via pgcrypto
- **Audit Logging:** Immutable audit trail for all write operations; stored separately
- **Rate Limiting:** Per-IP and per-user; stricter on auth endpoints
- **Input Validation:** Pydantic v2 strict mode on all API inputs
- **SQL Injection:** SQLAlchemy ORM parameterized queries; no raw SQL interpolation
- **XSS:** Content Security Policy headers; React's default escaping
- **CSRF:** SameSite=Strict cookies; CSRF tokens for form submissions
- **File Upload:** Type validation, size limits, virus scan (ClamAV), stored outside webroot

---

## 12. Implementation Roadmap

### Phase 1 — Foundation (Weeks 1–8) ← THIS BUILD
- Core data model + migrations
- Multi-tenant auth (JWT + RBAC)
- Client, Site, Asset management
- Incident lifecycle
- Alert notification engine (email + SMS)
- Basic SOAR playbooks (trigger → create incident → notify → create ticket)
- CCTV offline E2E flow
- Dashboard skeleton (Next.js)

### Phase 2 — Security Operations (Weeks 9–16)
- SOC module: event ingestion, SIEM correlation
- Vulnerability management
- Network security module
- Forensics & evidence management
- Elasticsearch integration
- Enhanced SOAR (multi-step, conditions, AI suggestions)
- Mobile app (React Native) for field technicians

### Phase 3 — Agency Operations & VIP (Weeks 17–24)
- Guard deployment management
- MDR/DDO regulatory reporting
- VIP protection module
- Training center management
- Advanced compliance dashboards
- RA 11917 / PNP-SOSIA report generation

---

*This document is the living design authority for the Power Tech Security platform. Update this document when architecture decisions change.*
