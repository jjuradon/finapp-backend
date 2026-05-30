# Feature Specification: Codebase Architecture Research

**Feature Branch**: `001-codebase-research`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Analyze this entire codebase. Document the architecture, key modules, data flows, integration points, and existing patterns. Focus on the finapp-backend modular monolith. Save the result as docs/codebase-research.md."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Onboarding & Context (Priority: P1)

A new developer joins the FamilyFinance team and needs to quickly understand the modular monolith structure, architecture, and technology stack of `finapp-backend` to start contributing.

**Why this priority**: Fundamental to developer velocity, reducing onboarding time, and establishing architectural alignment across the team.

**Independent Test**: A new team member can read the documentation and successfully answer architectural, structural, and toolchain questions without external guidance.

**Acceptance Scenarios**:

1. **Given** the codebase documentation is published, **When** a developer reads `docs/codebase-research.md`, **Then** they can identify the layers of the application, the boundaries of each module, and the role of each component.
2. **Given** the codebase documentation is published, **When** a developer reads `docs/codebase-research.md`, **Then** they can understand how to run tests, format code, and follow the project's architectural constraints (constitution).

---

### User Story 2 - Module Design & Interaction (Priority: P2)

An engineer needs to design a new module (such as `account` or `transaction`) and needs to know the exact patterns, directory layout, and separation of concerns expected in the system.

**Why this priority**: Ensures architectural consistency across future epics, modules, and database designs.

**Independent Test**: An engineer can create a new module skeleton following the exact structure documented.

**Acceptance Scenarios**:

1. **Given** the module integration documentation, **When** an engineer refers to the guidelines, **Then** they can structure the new module's API routes, service, and repository layers without violating cross-module boundaries.

---

### User Story 3 - Security & Integration Auditing (Priority: P3)

A security reviewer or senior engineer wants to inspect the existing security implementations (JWT signing, refresh token rotation, PKCE, rate-limiting, PII encryption) to verify they align with standard security practices.

**Why this priority**: Helps maintain high security standards and provides a central summary of protection mechanisms.

**Independent Test**: A security reviewer can audit the current auth/security setup using the documentation as a reference map.

**Acceptance Scenarios**:

1. **Given** the security section of the documentation, **When** an auditor checks the auth flow, **Then** they can verify all token management rules (such as HTTPOnly cookie settings and rotation revocation) are fully documented.

---

### Edge Cases

- **Module Encapsulation Violations**: What happens when a new module violates encapsulation rules (e.g. importing another module's models/repositories directly)? The codebase research and project constitution must explicitly call out that cross-module communication is restricted to service boundaries.
- **Documentation Drift**: How does the system handle documentation drift when new features are added? Future epics must update `docs/codebase-research.md` as their respective modules transition from scaffolding to fully implemented.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System architecture documentation MUST cover the overall structure, module boundaries, directory layout, and key technological choices of the backend.
- **FR-002**: Core module design (`auth_household`) MUST be documented detailing the models, services (CQRS pattern split), token handling, rate-limiting, and PII encryption.
- **FR-003**: Integration points (PostgreSQL/TimescaleDB, Redis, RabbitMQ) MUST be clearly documented with their respective roles in the system.
- **FR-004**: Testing structure, conftest setups, and development toolchain (uv, ruff, make targets) MUST be documented.
- **FR-005**: All codebase documentation MUST be saved in a single version-controlled markdown file at `docs/codebase-research.md`.

### Key Entities *(include if feature involves data)*

- **Codebase Research Document**: The resulting markdown file (`docs/codebase-research.md`) describing the architecture, modules, and constraints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Codebase research is fully documented in `docs/codebase-research.md` containing all required architectural, module, and security details.
- **SC-002**: The documentation is written in clear, technology-agnostic/business-aligned language in the specification (spec.md) and detailed technical language in the research document (codebase-research.md).
- **SC-003**: 100% of the functional requirements are addressed by the output document.

## Assumptions

- Codebase analysis is focused on the `finapp-backend` modular monolith repository.
- Sibling repositories (`finapp-gitops`, `finapp-mobile`, `finapp-web`) are referenced only where they integrate with the backend (e.g., ports, OIDC redirects).
