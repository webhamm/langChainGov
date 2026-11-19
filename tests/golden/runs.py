"""Builders for hand-made golden-set run files (fictional data only)."""

from datetime import UTC, datetime
from pathlib import Path

from langchaingov.golden.models import ModelProfile
from langchaingov.golden.store import CaseResult, RequestParams, RunHeader, RunWriter

NEEDLE_IDS = ["vault-door", "ferry-captain", "logbook-page", "orchard-password", "flood-month"]
REPLY = (
    "vault-door: heron blue\n"
    "ferry-captain: Ilsabet Morrow\n"
    "logbook-page: 4817\n"
    "orchard-password: copper finch\n"
    "flood-month: Brumewane"
)


def make_header(
    run_id: str = "20261119T100000Z-m",
    *,
    model: str = "m",
    set_sha: str = "5" * 64,
    generator_version: int = 1,
    levels: tuple[float, ...] = (0.25, 0.5),
    repeat: int = 1,
    context: int = 32768,
) -> RunHeader:
    return RunHeader(
        run_id=run_id,
        started_at=datetime.strptime(run_id[:15], "%Y%m%dT%H%M%S").replace(tzinfo=UTC),
        langchaingov_version="0.11.0",
        set_name="default",
        set_sha256=set_sha,
        generator_version=generator_version,
        model=model,
        profile=ModelProfile(name=model, context_tokens=context, local=True),
        params=RequestParams(
            temperature=0,
            max_tokens=1024,
            timeout_s=600,
            max_retries=0,
            seed_requested=1,
            seed_sent=1,
        ),
        counter="chars/4",
        base_url_host="localhost:4000",
        levels=list(levels),
        repeat=repeat,
    )


def make_case(
    case_id: str = "L025",
    *,
    repeat: int = 1,
    response: str = REPLY,
    missed: tuple[str, ...] = (),
    prompt_sha: str | None = None,
    finish: str = "stop",
    reported: int = 1000,
    latency_ms: int = 1000,
    error: str | None = None,
    truncation: bool = False,
) -> CaseResult:
    needles = {n: (n not in missed and error is None) for n in NEEDLE_IDS}
    return CaseResult(
        case_id=case_id,
        level=int(case_id[1:]) / 100,
        repeat=repeat,
        target_tokens=1000,
        est_tokens=990,
        prompt_sha256=prompt_sha or (case_id.lower() * 16)[:64],
        prompt_chars=3960,
        reported_prompt_tokens=None if error else reported,
        completion_tokens=None if error else 20,
        finish_reason=None if error else finish,
        latency_ms=latency_ms,
        response="" if error else response,
        needles=needles,
        recall=sum(needles.values()) / len(needles),
        suspected_truncation=truncation,
        error=error,
    )


def make_run(
    *cases: CaseResult,
    run_id: str = "20261119T100000Z-m",
    model: str = "m",
    set_sha: str = "5" * 64,
    generator_version: int = 1,
    context: int = 32768,
) -> tuple[RunHeader, list[CaseResult]]:
    """A header whose levels and repeat count match ``cases`` (default: L025 and L050)."""
    chosen = list(cases) or [make_case("L025"), make_case("L050")]
    header = make_header(
        run_id,
        model=model,
        set_sha=set_sha,
        generator_version=generator_version,
        levels=tuple(sorted({c.level for c in chosen})),
        repeat=max(c.repeat for c in chosen),
        context=context,
    )
    return header, chosen


def write_run(runs_dir: Path, header: RunHeader, cases: list[CaseResult]) -> Path:
    path = runs_dir / f"{header.run_id}.jsonl"
    with RunWriter(path, header) as writer:
        for case in cases:
            writer.append(case)
    return path
