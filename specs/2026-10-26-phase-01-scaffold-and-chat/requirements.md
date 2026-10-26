# Requirements — Phase 01: Scaffold and chat

Roadmap: Stage 1 — Foundation, phase 01. Branch (created when work starts): `feat/phase-01-scaffold-and-chat`. Depends on: none.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

## Goal

Run `langchaingov chat "..."` and get an answer from the local Llama through the LiteLLM proxy, with tests, lint, type checks, and CI in place for every later phase.

## Scope

### In scope

- `git init`, `.gitignore` (Python, `.env`, `.venv`), a GitHub remote created with `gh repo create`.
- uv project with `src/langchaingov/`, `pyproject.toml`, `.python-version` (3.12), `uv.lock`.
- `langchaingov.settings.Settings` (pydantic-settings): `LANGCHAINGOV_BASE_URL` (default `http://localhost:4000/v1`), `LANGCHAINGOV_MODEL`, `LITELLM_API_KEY`, `LANGCHAINGOV_TEMPERATURE` (default 0). `.env.example` committed, `.env` ignored.
- `langchaingov.llm.make_chat_model(settings) -> BaseChatModel` returning a `ChatOpenAI` pointed at LiteLLM. The single place that knows about LiteLLM.
- `langchaingov chat "<prompt>"` with `--system`, `--model`, `--json`. Prints the reply, or `{"model": ..., "reply": ...}` with `--json`. Exit code 1 with a clear message if LiteLLM is unreachable or rejects the key.
- `langchaingov version`.
- `Makefile` with `check`, `lint`, `format`, `typecheck`, `test` targets.
- GitHub Actions workflow running `make check` on push and PR.
- Tests: settings load from env, `chat` works with a fake chat model injected via a factory override, `--json` output shape, exit codes.
- README rewritten: what the project is, setup (uv, LiteLLM, `.env`), commands.

### Out of scope

- Any guardrail logic (phase 02).
- Streaming output (Later / optional unless the user asks for it).
- Conversation memory or multi-turn chat.

## Open questions

Check in with the user on each of these before implementing; if the answers change the phase plan, update `specs/roadmap.md` too.

- What model name does the LiteLLM proxy expose for the local Llama (the value of `LANGCHAINGOV_MODEL`)? `curl http://localhost:4000/v1/models` with the key will list it. **Resolved:** to be discovered from `/v1/models` (or supplied by the user) before the manual check; the value lives only in `.env`.
- Where does the LiteLLM API key live for local runs: `.env` file (recommended) or shell environment only? **Resolved:** `.env` file, git-ignored, with `.env.example` committed.
- Pin Python 3.12 via uv (recommended, for guardrails-ai and nemoguardrails compatibility) or use the system 3.15 and accept that later phases may be blocked? **Resolved:** pin Python 3.12 via uv.
- GitHub repo name and visibility: `webhamm/langChainGov`, private (recommended) or public? **Resolved:** `webhamm/langChainGov`, private.

(When the phase starts, append ` **Resolved:** <answer>.` to each question.)

## Context

- `tech-stack.md` → one model factory (`make_chat_model`) is the only code that knows about LiteLLM; tests inject fakes.
- `mission.md` principle 1 (local first) and principle 4 (tests never touch the network).
