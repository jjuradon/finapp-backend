dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/

lint:
	ruff check app tests
	black --check app tests

migrate:
	alembic upgrade head

build:
	docker build -t finapp-backend .
