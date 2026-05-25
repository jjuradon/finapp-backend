# FamilyFinance Backend (`finapp-backend`)

This repository contains the Phase 1 Modular Monolith codebase for the FamilyFinance budget planning application.

## Tooling & Architecture
This modular monolith is built using:
- **Python 3.12**
- **FastAPI** for ASGI routes
- **SQLAlchemy 2.0 async** with **Alembic** migrations
- **Uvicorn** async web server
- **Ruff** & **Black** for style enforcement and linting
- **pre-commit** hooks for commits verification (including `detect-secrets`)

## Port Assignments
- **8000**: FastAPI App (`main.py`)
- **5432**: PostgreSQL / TimescaleDB
- **6379**: Redis
- **5672**: RabbitMQ AMQP Broker
- **15672**: RabbitMQ Management UI
- **80**: Nginx reverse proxy / API gateway

## Quick Start

### 1. Prerequisites
Ensure you have the following installed on your host system:
- Docker and Docker Compose
- `uv` (modern Python package and environment manager)
- Git

### 2. Environment Setup
Copy the env example file and fill in required secrets (using placeholders for local dev):
```bash
cp .env.example .env
```

### 3. Setup and Installation
Install all dependencies, configure the environment, and wire up pre-commit hooks:
```bash
make install
```
*Note: uv creates and manages `.venv` automatically — you do not need to activate it manually.*

### 4. Running the Infrastructure
To start the infrastructure dependencies, copy the `.env.example` to `.env` in `finapp-gitops` and run:
```bash
make dev
```
in the sibling `finapp-gitops` repository.

## Backend Makefile Targets
We provide a set of Makefile commands for standard tasks inside `finapp-backend/Makefile`:
- `make install`: Sets up the `.venv` directory, installs dependencies, wires pre-commit, and generates the `detect-secrets` baseline.
- `make lint`: Checks codebase with Ruff and Black formatters.
- `make test`: Runs pytest suite with coverage enforcement.
- `make build`: Builds the backend Docker image tagged with the current Git commit SHA.
- `make audit`: Runs `pip-audit` via `uvx`.

For stack orchestration targets (like `up`, `down`, `logs`, `migrate`, `ps`), refer to the sibling repository [finapp-gitops](file:///home/jjuradon/finapp/finapp-gitops).
