# finapp-backend

FastAPI modular monolith serving as the main backend for FamilyFinance. It includes a health endpoint and database/broker connectivity verification.

## Running Locally

To run the backend directly:
```bash
make dev
```

Alternatively, you can run the entire stack via the `finapp-gitops` repository:
```bash
cd ../finapp-gitops && make up
```

## Setup
Install pre-commit hooks to ensure formatting (Ruff, Black) and secrets detection:
```bash
pre-commit install
```
