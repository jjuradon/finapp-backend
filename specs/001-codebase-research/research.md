# Research: Codebase Architecture

## Decision: Documentation Strategy
**Decision:** We will create a comprehensive architectural overview document at `docs/codebase-research.md` documenting the modular monolith structure, module interactions, data flows, and security constraints.
**Rationale:** The feature specification requires documenting the existing structure of `finapp-backend` to aid developer onboarding, cross-module development, and security auditing.
**Alternatives considered:** Using multiple separate markdown files per module. Rejected because a centralized map provides a better overview for onboarding.

## Needs Clarification Resolutions
- Language/Version: Python 3.11 with FastAPI (deduced from pyproject.toml / uv environment).
- Architecture: Modular monolith separated into `app/modules/*` with CQRS service separation and isolated database schemas via Alembic.
- Storage: PostgreSQL (with TimescaleDB for time-series) and Redis for caching/rate-limiting. RabbitMQ for asynchronous events.
- Security: JWTs in memory, Refresh tokens as HttpOnly cookies, PII encrypted with AES-256-GCM.
