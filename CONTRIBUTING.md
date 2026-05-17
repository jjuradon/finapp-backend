# Contributing to finapp-backend

## Repo purpose
FastAPI modular monolith serving as the main backend for FamilyFinance.

## Running locally
Use `make dev` to run locally, or `docker compose up` via gitops.

## Adding a new feature
See agent rules and patterns. Layers: router -> service -> repository -> model.

## Pre-commit setup
Run `pre-commit install`.

## Tests
Run `make test`.
