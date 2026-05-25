.PHONY: install lint test build audit

# Install all dependencies (including dev group) from the lockfile.
# Run once after cloning. Re-run after any pyproject.toml change.
# Also installs pre-commit hooks and generates the detect-secrets baseline.
# uv creates and manages .venv automatically — never activate it manually.
install:
	uv sync --frozen
	uv run pre-commit install
	uv run detect-secrets scan > .secrets.baseline

# Run Ruff linter and Black formatter check (read-only, no auto-fix, no Docker).
# Exits non-zero on any violation.
# Used by pre-commit hooks and GitHub Actions CI lint job.
lint:
	uv run ruff check .
	uv run black --check .

# Run full pytest suite with coverage enforcement.
# Requires TEST_DATABASE_URL env var pointing at any accessible PostgreSQL.
#   Local: export TEST_DATABASE_URL=postgresql+asyncpg://finapp:changeme@localhost:5432/finapp_test
#          (the PG instance started by `make dev` in finapp-gitops works fine)
#   CI:    provided automatically by the GitHub Actions postgres service.
# Exits non-zero if any test fails or coverage drops below threshold.
test:
	uv run pytest tests/ --cov=app --cov-fail-under=80 -v

# Build the backend Docker image tagged with the current git commit SHA.
# Does NOT push. Push is a CI-only operation.
build:
	docker build \
	    -t ghcr.io/familyfinance/finapp-backend:$(shell git rev-parse --short HEAD) \
	    .

# Run pip-audit via uvx (no install needed — uvx runs it in an isolated env).
# Fails on any high or critical CVE finding.
audit:
	uvx pip-audit
