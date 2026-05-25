# Contributing to FamilyFinance Backend

Welcome to the FamilyFinance backend contributor guide! Please follow the rules and guidelines below to maintain system consistency, reliability, and security.

---

## 1. Setup and Workflow

### Clone and Setup
1. Ensure you have `uv` installed system-wide: [uv Installation Guide](https://docs.astral.sh/uv/getting-started/installation/).
2. Clone both repositories (`finapp-backend` and `finapp-gitops`).
3. Set up the backend developer environment (one-time):
   ```bash
   make install
   ```
   This creates the `.venv` virtual environment, installs dependencies, wires up pre-commit hooks, and writes the initial `.secrets.baseline` file.
4. Set up the local infrastructure stack:
   ```bash
   # Go to the gitops repository
   cp .env.example .env
   make dev
   ```

---

## 2. Layer Import Rules

*Quoted verbatim from Architecture Baseline Section 5.1:*

```
routes/  →  services/  →  repositories/  →  models/
                      ↘  schemas/
                      ↘  utils/
```

- `routes/` may only import from `services/` and `schemas/`.
- `services/` may only import from `repositories/`, `schemas/`, and `utils/`.
- `repositories/` may only import from `models/` and `db/`.
- No module may import another module's `models/` or `repositories/`.

---

## 3. Key Constraints & Anti-Patterns

*Quoted verbatim from Architecture Baseline Section 8:*

The following are treated as bugs in code review:

- A module importing another module's `models/` or `repositories/`
- `os.environ.get()` outside `core/config.py`
- JWT stored in `localStorage` or `sessionStorage`
- `Base.metadata.create_all()` in any non-test file
- A route handler returning a raw SQLAlchemy model (use a Pydantic schema)
- `float` type for any monetary value
- `try/except Exception: pass`
- `print()` in non-test code
- Hardcoded secrets or IP addresses outside config files
- Raw SQL string interpolation (`f"SELECT … {user_input}"`)
- A test that passes before the implementation exists

---

## 4. Running Tests & Coverage

We enforce test coverage requirements for all changes:
- Run the full test suite using:
  ```bash
  make test
  ```
- Coverage threshold of at least **80%** (via `--cov-fail-under=80`) is required and enforced in CI.

---

## 5. Adding a New Module

If you need to introduce a new backend module, follow this recipe:

1. Scaffold the folder structure inside `app/modules/<new_module>/`:
   - `api/routes/v1/.gitkeep`
   - `models/.gitkeep`
   - `repositories/.gitkeep`
   - `services/.gitkeep`
   - `schemas/.gitkeep`
   - `utils/.gitkeep`
2. Implement your route router inside `api/routes/v1/`.
3. Register your module router in the root `main.py` file:
   ```python
   # e.g. app.include_router(auth_router, prefix="/v1/auth")
   ```

---

## 6. Branch Naming Conventions

All commits should be made on descriptive branches matching the following patterns:
- `feat/epic-name` — for new features and capabilities.
- `fix/description` — for bug fixes.
- `chore/description` — for maintenance, dependencies updates, tooling, etc.
