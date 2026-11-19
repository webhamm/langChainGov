"""Compare a golden-set run with a baseline run, per fill level.

Comparison has two steps:

1. **Is it the same test?** Same set content, same generator version, and the same
   prompt bytes (SHA-256) for every level both runs have. If not, the result is
   ``NOT COMPARABLE`` with the reason, never drift: a different prompt is a different test.
2. **Did the answers move?** Per level, repeats are aggregated: each needle's recall
   rate, the lowest text similarity of a current reply to its best-matching baseline
   reply, and mean length, latency, and reported prompt tokens.

Drift (the model's answers changed): a needle's recall rate dropped, similarity fell
below the threshold, the finish reason changed, or a case errored. Environment warnings
(the setup changed, not necessarily the model): reported prompt tokens moved beyond the
threshold, or truncation is newly suspected. Latency is shown but never flagged; local
runs vary too much.
"""

from difflib import SequenceMatcher
from statistics import mean
from typing import Literal

from pydantic import BaseModel, Field

from langchaingov.golden.store import CaseResult, RunHeader

Verdict = Literal["STABLE", "DRIFT", "NOT COMPARABLE"]


class Thresholds(BaseModel):
    min_similarity: float = 0.90
    prompt_token_pct: float = 2.0


class Flag(BaseModel):
    kind: Literal["drift", "environment"]
    case_id: str
    metric: str
    detail: str
    """Says what moved, by how much, and against which threshold."""


class LevelRow(BaseModel):
    case_id: str
    level: float
    baseline_recall: float
    current_recall: float
    lost: list[str]
    gained: list[str]
    similarity: float | None
    """``None`` when every current case errored."""
    length_change_pct: float | None
    latency_change_pct: float | None
    prompt_tokens_change_pct: float | None
    baseline_finish: list[str]
    current_finish: list[str]
    current_errors: int
    repeats: dict[str, int]
    """How many cases each side had at this level."""


class DriftReport(BaseModel):
    baseline_run_id: str
    current_run_id: str
    verdict: Verdict
    reasons: list[str] = Field(default_factory=list)
    """Why the runs are not comparable."""
    rows: list[LevelRow] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)
    not_compared: list[str] = Field(default_factory=list)
    """Levels only one of the runs has."""


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def compare_runs(
    baseline: tuple[RunHeader, list[CaseResult]],
    current: tuple[RunHeader, list[CaseResult]],
    thresholds: Thresholds,
    cross_model: bool = False,
) -> DriftReport:
    (b_header, b_cases), (c_header, c_cases) = baseline, current
    report = DriftReport(
        baseline_run_id=b_header.run_id, current_run_id=c_header.run_id, verdict="STABLE"
    )
    b_levels, c_levels = _by_case(b_cases), _by_case(c_cases)
    shared = [cid for cid in b_levels if cid in c_levels]
    report.not_compared = sorted(set(b_levels) ^ set(c_levels))

    report.reasons = _incompatibilities(b_header, c_header, b_levels, c_levels, shared, cross_model)
    if report.reasons:
        report.verdict = "NOT COMPARABLE"
        return report

    for cid in shared:
        row, flags = _compare_level(cid, b_levels[cid], c_levels[cid], thresholds)
        report.rows.append(row)
        report.flags.extend(flags)
    if any(f.kind == "drift" for f in report.flags):
        report.verdict = "DRIFT"
    return report


def _by_case(cases: list[CaseResult]) -> dict[str, list[CaseResult]]:
    grouped: dict[str, list[CaseResult]] = {}
    for case in sorted(cases, key=lambda c: (c.level, c.repeat)):
        grouped.setdefault(case.case_id, []).append(case)
    return grouped


def _incompatibilities(
    b: RunHeader,
    c: RunHeader,
    b_levels: dict[str, list[CaseResult]],
    c_levels: dict[str, list[CaseResult]],
    shared: list[str],
    cross_model: bool,
) -> list[str]:
    reasons: list[str] = []
    if b.set_sha256 != c.set_sha256:
        reasons.append(f"golden set content differs ({b.set_name!r} vs {c.set_name!r} hashes)")
    if b.generator_version != c.generator_version:
        reasons.append(f"generator version {b.generator_version} vs {c.generator_version}")
    if b.model != c.model and not cross_model:
        reasons.append(f"model {b.model!r} vs {c.model!r} (pass --cross-model to compare anyway)")
    for cid in shared:
        b_sha, c_sha = b_levels[cid][0].prompt_sha256, c_levels[cid][0].prompt_sha256
        if b_sha != c_sha:
            reasons.append(
                f"{cid} prompt differs ({b_sha[:12]} vs {c_sha[:12]}); "
                f"context {b.profile.context_tokens} vs {c.profile.context_tokens} tokens"
            )
    if not shared:
        reasons.append("the runs have no fill level in common")
    return reasons


def _compare_level(
    cid: str, base: list[CaseResult], cur: list[CaseResult], t: Thresholds
) -> tuple[LevelRow, list[Flag]]:
    flags: list[Flag] = []
    b_ok = [c for c in base if not c.error]
    c_ok = [c for c in cur if not c.error]
    errors = len(cur) - len(c_ok)
    if errors:
        flags.append(Flag(kind="drift", case_id=cid, metric="error", detail=_errors(cur)))

    # Needle recall rates: the share of repeats in which each needle was recalled.
    b_rates, c_rates = _rates(b_ok), _rates(c_ok)
    lost = [n for n, rate in b_rates.items() if c_ok and c_rates.get(n, 0.0) < rate]
    gained = [n for n, rate in c_rates.items() if rate > b_rates.get(n, 0.0)]
    for needle in lost:
        detail = f"{needle}: recall {b_rates[needle]:.0%} -> {c_rates.get(needle, 0.0):.0%}"
        flags.append(Flag(kind="drift", case_id=cid, metric="needle lost", detail=detail))

    # Every current reply should closely match at least one baseline reply.
    sim: float | None = None
    if c_ok and b_ok:
        sim = min(max(similarity(b.response, c.response) for b in b_ok) for c in c_ok)
        if sim < t.min_similarity:
            detail = f"text similarity {sim:.3f} < {t.min_similarity:.2f}"
            flags.append(Flag(kind="drift", case_id=cid, metric="similarity", detail=detail))

    b_finish = sorted({c.finish_reason or "-" for c in b_ok})
    c_finish = sorted({c.finish_reason or "-" for c in c_ok})
    if c_ok and b_finish != c_finish:
        detail = f"finish {'/'.join(b_finish)} -> {'/'.join(c_finish)}"
        flags.append(Flag(kind="drift", case_id=cid, metric="finish reason", detail=detail))

    tokens_pct = _pct(
        _mean_of(b_ok, "reported_prompt_tokens"), _mean_of(c_ok, "reported_prompt_tokens")
    )
    if tokens_pct is not None and abs(tokens_pct) > t.prompt_token_pct:
        detail = f"reported prompt tokens {tokens_pct:+.1f}% (> {t.prompt_token_pct:g}%)"
        flags.append(Flag(kind="environment", case_id=cid, metric="prompt tokens", detail=detail))
    if any(c.suspected_truncation for c in c_ok) and not any(b.suspected_truncation for b in b_ok):
        detail = "suspected truncation (the server served less than the prompt)"
        flags.append(Flag(kind="environment", case_id=cid, metric="truncation", detail=detail))

    row = LevelRow(
        case_id=cid,
        level=base[0].level,
        baseline_recall=mean(c.recall for c in b_ok) if b_ok else 0.0,
        current_recall=mean(c.recall for c in c_ok) if c_ok else 0.0,
        lost=lost,
        gained=gained,
        similarity=sim,
        length_change_pct=_pct(_mean_len(b_ok), _mean_len(c_ok)),
        latency_change_pct=_pct(_mean_of(b_ok, "latency_ms"), _mean_of(c_ok, "latency_ms")),
        prompt_tokens_change_pct=tokens_pct,
        baseline_finish=b_finish,
        current_finish=c_finish,
        current_errors=errors,
        repeats={"baseline": len(base), "current": len(cur)},
    )
    return row, flags


def _rates(cases: list[CaseResult]) -> dict[str, float]:
    if not cases:
        return {}
    return {n: mean(1.0 if c.needles.get(n) else 0.0 for c in cases) for n in cases[0].needles}


def _mean_of(cases: list[CaseResult], field: str) -> float | None:
    values = [v for c in cases if isinstance(v := getattr(c, field), int)]
    return mean(values) if values else None


def _mean_len(cases: list[CaseResult]) -> float | None:
    return mean(len(c.response) for c in cases) if cases else None


def _pct(before: float | None, after: float | None) -> float | None:
    if before is None or after is None or before == 0:
        return None
    return round((after - before) / before * 100, 2)


def _errors(cases: list[CaseResult]) -> str:
    failed = [c for c in cases if c.error]
    first = failed[0].error or ""
    return f"{len(failed)} of {len(cases)} repeats errored ({first[:80]})"
