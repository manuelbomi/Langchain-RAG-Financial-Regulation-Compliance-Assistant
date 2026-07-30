# Makefile for local development. Targets are intentionally thin wrappers
# around the underlying tools so CI (.github/workflows/ci.yml) and local
# development always run the exact same commands.

.PHONY: install test lint typecheck run docker-build docker-run reindex fmt

install:
	pip install -r requirements-dev.txt
	pip install -e .

test:
	pytest -v --cov=compliance_copilot --cov-report=term-missing

lint:
	ruff check src tests

fmt:
	ruff format src tests
	ruff check --fix src tests

typecheck:
	mypy src

run:
	uvicorn compliance_copilot.api.main:app --host 0.0.0.0 --port 8000 --reload

reindex:
	python scripts/build_index.py

docker-build:
	docker build -t compliance-copilot:local .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env compliance-copilot:local
