.PHONY: check lint format format-check typecheck test llm-up llm-down llm-status llm-smoke

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

# Local model stack: Ollama (llama3.2:3b, 32k window) behind a repo-owned LiteLLM proxy.
# See scripts/llm/ and infra/. Override defaults with env vars, e.g. LLM_PORT=4001.
llm-up:
	@scripts/llm/up.sh

llm-down:
	@scripts/llm/down.sh

llm-status:
	@scripts/llm/status.sh

llm-smoke:
	@scripts/llm/smoke.sh
