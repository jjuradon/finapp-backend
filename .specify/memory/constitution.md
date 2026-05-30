<!--
Version change: N/A → 1.0.0
Added principles: Architecture, Code Quality, API Design, Database, Security, Testing, Governance
-->

# FamilyFinance Constitution

## Core Principles

### Architecture
All modules follow internal layering: routes → services → repositories → models. No module may import another module's models or repositories directly. Cross‑module reads go through public services (in‑process). Monetary values stored as NUMERIC(18,2) in DB and strings in API. Timestamps use timestamptz.

### Code Quality
Environment variables accessed only via `core/config.py` using `pydantic-settings`. No `print()` in production code; use structured `logger`. Database schema modified only via Alembic migrations. No raw SQL string interpolation. Exceptions are explicitly caught; no blanket `except Exception: pass`. Route handlers return Pydantic schemas, never raw SQLAlchemy models.

### API Design
All routes versioned from day one (`/v1/...`). Responses follow envelope `{ data, meta: { request_id, timestamp }, error }`. List endpoints use cursor‑based pagination. New string fields have explicit `max_length` in Pydantic and matching VARCHAR(n) in migrations.

### Database
Each table includes `id` (UUID, `gen_random_uuid()`), `created_at` and `updated_at` as `timestamptz`. Schema changes exclusively via Alembic. Per‑module DB users with schema‑scoped permissions.

### Security
JWTs stored only in server memory; never in `localStorage` or `sessionStorage`. Refresh tokens delivered as HttpOnly cookies. Sensitive fields (ssn, date_of_birth, account_number) encrypted with AES‑256‑GCM at rest.

### Testing
Minimum 80% line coverage for services, 70% for API routes. Tests use `pytest` with `pytest‑asyncio`; no `unittest`. Tests must not make real network calls. Tests must verify implementation exists; false‑positive placeholder tests are prohibited.

### Governance
All changes must be reviewed for compliance with the above principles. Amendments require documentation and approval.

**Version**: 1.0.0 | **Ratified**: 2026-05-30 | **Last Amended**: 2026-05-30
