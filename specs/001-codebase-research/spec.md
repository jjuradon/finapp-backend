# Feature Specification: Codebase Architecture Research

**Feature Branch**: `001-codebase-research`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Analyze this entire codebase. Document the architecture, key modules, data flows, integration points, and existing patterns. Focus on the finapp-backend modular monolith. Save the result as docs/codebase-research.md."
Reference: `asset-docs/architecture-baseline-v1.1.md`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Onboarding & Context (Priority: P1)

A new developer joins the FamilyFinance team and needs to quickly understand the modular monolith structure, architecture, and technology stack of `finapp-backend` to start contributing.

**Why this priority**: Fundamental to developer velocity, reducing onboarding time, and establishing architectural alignment across the team.

**Independent Test**: A new team member can read the documentation and successfully answer architectural, structural, and toolchain questions (including the Makefile split, `uv` package manager usage, and Phase 1 vs Phase 2 progression) without external guidance.

**Acceptance Scenarios**:

1. **Given** the codebase documentation is published, **When** a developer reads `docs/codebase-research.md`, **Then** they can identify the layers of the application, the 6 core modules, and the role of each component.
2. **Given** the codebase documentation is published, **When** a developer reads `docs/codebase-research.md`, **Then** they can understand how to run tests using the database isolation pattern, format code with Ruff/Black, and follow the project's architectural constraints.

---

### User Story 2 - Module Design & Interaction (Priority: P2)

An engineer needs to design a new module or modify an existing one and needs to know the exact patterns, directory layout, separation of concerns, and migration standards expected in the system.

**Why this priority**: Ensures architectural consistency across future epics, modules, and database designs.

**Independent Test**: An engineer can create a new module skeleton following the exact structure documented, including the code-first Alembic migration workflow.

**Acceptance Scenarios**:

1. **Given** the module integration documentation, **When** an engineer refers to the guidelines, **Then** they can structure the new module's API routes, service, and repository layers without violating cross-module boundaries.
2. **Given** the migration standard section, **When** an engineer needs to update the database schema, **Then** they can execute the code-first Alembic workflow correctly.

---

### User Story 3 - Security & Integration Auditing (Priority: P3)

A security reviewer or senior engineer wants to inspect the existing security implementations (OIDC Authorization Server, JWT signing, refresh token rotation, PKCE, rate-limiting, PII encryption) to verify they align with standard security practices.

**Why this priority**: Helps maintain high security standards and provides a central summary of protection mechanisms.

**Independent Test**: A security reviewer can audit the current auth/security setup and cross-cutting concerns using the documentation as a reference map.

**Acceptance Scenarios**:

1. **Given** the security section of the documentation, **When** an auditor checks the auth flow, **Then** they can verify all token management rules and OIDC compliance scopes are fully documented.

---

### Edge Cases

- **Module Encapsulation Violations**: What happens when a new module violates encapsulation rules (e.g. importing another module's models/repositories directly)? The codebase research and project constitution must explicitly call out that cross-module communication is restricted to service boundaries.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System architecture documentation MUST cover the overall structure, module boundaries (6 core modules), directory layout, and key technological choices of the backend (e.g., Python 3.12, FastAPI).
- **FR-002**: Core module design MUST be documented detailing the models, services (CQRS pattern split), token handling (OIDC + PKCE), rate-limiting, and PII encryption.
- **FR-003**: Integration points (PostgreSQL/TimescaleDB, Redis, RabbitMQ) MUST be clearly documented with their respective roles in the system.
- **FR-004**: Testing structure (database isolation pattern), toolchain (`uv`, Ruff, Black), and Makefile split MUST be documented.
- **FR-005**: All codebase documentation MUST be saved in a single version-controlled markdown file at `docs/codebase-research.md`.
- **FR-006**: The documentation MUST detail the codebase's progression from a Phase 1 modular monolith to Phase 2 microservices.
- **FR-007**: The documentation MUST outline the code-first database migration standard using Alembic.

### Key Entities *(include if feature involves data)*

- **Codebase Research Document**: The resulting markdown file (`docs/codebase-research.md`) describing the architecture, modules, and constraints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Codebase research is fully documented in `docs/codebase-research.md` containing all required architectural, module, and security details aligned with Architecture Baseline v1.1.
- **SC-002**: 100% of the functional requirements are addressed by the output document.

## Assumptions

- Codebase analysis is focused on the `finapp-backend` modular monolith repository.
- Sibling repositories (`finapp-gitops`, `finapp-mobile`, `finapp-web`) are referenced only where they integrate with the backend (e.g., Makefile separation, OIDC redirects).
