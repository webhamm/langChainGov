# Plan — Phase 02: Guardrail core

Roadmap: Stage 1 — Foundation, phase 02. Branch (created when work starts): `feat/phase-02-guardrail-core`. Depends on: phase 01.

> **Outline spec.** Scope and decisions are tentative. Resolve the open questions and expand this spec with the user before work starts on this phase.

See `requirements.md` for scope and decisions, and `validation.md` for the merge bar.

## 1. Branch

1.1. Create `feat/phase-02-guardrail-core` from `main`, with phase 01 merged.

## 2. Protocol and chain

2.1. `src/langchaingov/guards/base.py`: `Verdict`, `GuardedResult` (pydantic), `Guardrail` (typing.Protocol, runtime-checkable). Tests in `tests/guards/test_base.py` for validation (reason required when not allow).
2.2. `src/langchaingov/guards/registry.py`: module-level dict, `register`, `get`, `names`, `UnknownGuardError`. Tests in `tests/guards/test_registry.py`.
2.3. `src/langchaingov/chain.py`: `GuardedChain(model, guards)` with `invoke(prompt, system=None) -> GuardedResult`. Tests in `tests/test_chain.py` with `FakeListChatModel` and stub guards.

## 3. First guard

3.1. `src/langchaingov/guards/custom/keyword_blocklist.py`: `KeywordBlocklist(words)`; case-insensitive whole-word match; registered as `keyword-blocklist`. Settings gain `blocklist: list[str]`. Tests in `tests/guards/test_keyword_blocklist.py`.

## 4. CLI

4.1. `guard` typer sub-app in `src/langchaingov/cli.py` (or `cli/guard.py`): `list` and `run`. Rich table for verdicts in text mode; `--json` dumps `GuardedResult`. Tests in `tests/test_cli_guard.py`.

## 5. Wrap-up

5.1. Bump the version to `0.2.0` (pyproject and `__version__` must match).
5.2. Update the README for `guard list` and `guard run`.
5.3. Mark phase 02 done in `specs/roadmap.md`.
5.4. Work through `validation.md` and record the results.
