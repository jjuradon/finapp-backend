# Tasks: Codebase Architecture Research

**Input**: Design documents from `/specs/001-codebase-research/` and Architecture Baseline v1.1

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create `docs/` directory if it does not exist
- [x] T002 Initialize `docs/codebase-research.md` file with a title and basic outline based on the feature spec and Architecture Baseline v1.1

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Gather overall modular monolith architecture overview (including Phase 1 vs Phase 2 progression) to serve as the foundation of the document

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Developer Onboarding & Context (Priority: P1) 🎯 MVP

**Goal**: A new developer can read the documentation and successfully answer architectural, structural, and toolchain questions without external guidance.

**Independent Test**: A new team member can identify layers of the application, the 6 core modules, and boundaries of each module.

### Implementation for User Story 1

- [x] T004 [US1] Document application layers, boundaries, the 6 core modules, and the role of each component in `docs/codebase-research.md`
- [x] T005 [US1] Document how to run tests (database isolation pattern), format code (Ruff/Black), and the development toolchain (`uv`, Makefile split) in `docs/codebase-research.md`
- [x] T006 [US1] Document project's architectural constraints (constitution and anti-patterns) in `docs/codebase-research.md`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Module Design & Interaction (Priority: P2)

**Goal**: An engineer can design a new module knowing the exact patterns, directory layout, and separation of concerns.

**Independent Test**: An engineer can create a new module skeleton following the exact structure documented and execute the Alembic workflow correctly.

### Implementation for User Story 2

- [x] T007 [US2] Document exact patterns, directory layout, and separation of concerns expected in the system in `docs/codebase-research.md`
- [x] T008 [US2] Detail the core module design including CQRS pattern split, Saga, and Outbox patterns in `docs/codebase-research.md`
- [x] T009 [US2] Document cross-module communication rules (restricted to service boundaries) in `docs/codebase-research.md`
- [x] T010 [US2] Document the code-first database migration standard using Alembic in `docs/codebase-research.md`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Security & Integration Auditing (Priority: P3)

**Goal**: A security reviewer can inspect the existing security implementations to verify they align with standard practices.

**Independent Test**: An auditor can verify all token management rules, OIDC compliance, and security protections are fully documented.

### Implementation for User Story 3

- [x] T011 [US3] Document existing security implementations (OIDC Authorization Server, JWT signing, refresh token rotation, PKCE, rate-limiting, PII encryption) in `docs/codebase-research.md`
- [x] T012 [US3] Document integration points (PostgreSQL/TimescaleDB, Redis, RabbitMQ) and their respective roles in `docs/codebase-research.md`
- [x] T013 [US3] Document cross-cutting concerns like multi-jurisdiction compliance and field-level encryption in `docs/codebase-research.md`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T014 Review and format `docs/codebase-research.md` for clarity, verifying it meets all functional requirements (FR-001 to FR-007)
- [x] T015 Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Expands on US1 structure
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Expands on US1/US2 structure

### Within Each User Story

- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
