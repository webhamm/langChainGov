.PHONY: check lint format format-check typecheck test

check: lint format-check typecheck test

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

format-check:
	uv run ruff format --check src tests

typecheck:
	uv run mypy

test:
	uv run pytest
