# Plan — Phase 01: Scaffold and chat

Roadmap: Stage 1 — Foundation, phase 01. Branch (created when work starts): `feat/phase-01-scaffold-and-chat`. Depends on: none.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. `git init`, commit the specs on `main`, `gh repo create` with the chosen name and visibility, push `main`.
1.2. Create `feat/phase-01-scaffold-and-chat` from `main`.

## 2. Project scaffold

2.1. `uv init --package --name langchaingov`, set `.python-version` to 3.12, `uv python install 3.12`. Add deps: `langchain`, `langchain-openai`, `typer`, `rich`, `pydantic-settings`. Dev deps: `pytest`, `ruff`, `mypy`.
2.2. `pyproject.toml`: `[project.scripts] langchaingov = "langchaingov.cli:app"`, ruff and mypy strict config, `version = "0.1.0"`. `src/langchaingov/__init__.py` exposes `__version__`.
2.3. `Makefile` targets: `lint` (ruff check), `format` (ruff format), `typecheck` (mypy src tests), `test` (pytest), `check` (lint + format --check + typecheck + test).
2.4. `.gitignore`, `.env.example`, `.github/workflows/ci.yml` (uv setup action, `uv sync`, `make check`).

## 3. Settings and model factory

3.1. `src/langchaingov/settings.py`: `Settings(BaseSettings)` with the fields in requirements, `env_prefix="LANGCHAINGOV_"`, `LITELLM_API_KEY` read via an alias. Tests in `tests/test_settings.py` using `monkeypatch.setenv`.
3.2. `src/langchaingov/llm.py`: `make_chat_model(settings, model=None) -> BaseChatModel` building `ChatOpenAI(base_url=settings.base_url, api_key=settings.api_key, model=..., temperature=...)`. Test asserts the constructed model carries the base URL and model name without calling the network.

## 4. CLI

4.1. `src/langchaingov/cli.py`: typer app with `version` and `chat` commands. `chat` accepts prompt, `--system`, `--model`, `--json`. The model is obtained through a module-level factory hook so tests can substitute `FakeListChatModel`.
4.2. Error handling: catch connection and auth errors from the OpenAI client, print a one-line hint (is LiteLLM running on :4000, is the key set), exit 1.
4.3. Tests in `tests/test_cli.py` with `typer.testing.CliRunner`: plain output, `--json` shape, `--system` is passed as a system message, exit code 1 on a fake that raises a connection error.

## 5. Docs

5.1. Rewrite `README.md`: purpose, prerequisites (uv, LiteLLM on :4000), setup (`uv sync`, copy `.env.example`), commands, `make check`.

## 6. Wrap-up

6.1. Version is `0.1.0` in `pyproject.toml` and `__version__`.
6.2. README covers `chat` and `version`.
6.3. Mark phase 01 done in `specs/roadmap.md`.
6.4. Work through `validation.md` and record the results.
