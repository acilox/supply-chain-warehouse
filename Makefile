.PHONY: help install lint format test run-sample docker-up docker-down build-warehouse clean

PYTHON := python3
VENV := .venv

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -e ".[dev]"

lint:
	$(VENV)/bin/ruff check src tests

format:
	$(VENV)/bin/black src tests
	$(VENV)/bin/ruff check --fix src tests

test:
	$(VENV)/bin/pytest -v

run-sample:  ## Run pipeline against sample CSVs
	$(VENV)/bin/python -m supply_chain_dw.main run --source sample

build-warehouse:  ## Print Snowflake DDL (must be applied manually)
	@cat sql/ddl/snowflake_starschema.sql

docker-up:
	docker compose up -d

docker-down:
	docker compose down -v

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
