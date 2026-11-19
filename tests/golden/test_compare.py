import pytest

from langchaingov.golden.compare import Thresholds, compare_runs, similarity
from langchaingov.golden.store import CaseResult, RunHeader
from tests.golden.runs import REPLY, make_case, make_run

T = Thresholds()
Run = tuple[RunHeader, list[CaseResult]]


def run(
    *cases: CaseResult,
    model: str = "m",
    set_sha: str = "5" * 64,
    generator_version: int = 1,
) -> Run:
    return make_run(*cases, model=model, set_sha=set_sha, generator_version=generator_version)


def base() -> Run:
    return run(make_case("L025"), make_case("L050"))


def test_identical_runs_are_stable() -> None:
    report = compare_runs(base(), base(), T)
    assert report.verdict == "STABLE" and report.flags == []
    assert [r.similarity for r in report.rows] == [1.0, 1.0]
    assert report.rows[0].baseline_recall == report.rows[0].current_recall == 1.0


@pytest.mark.parametrize(
    ("current", "reason"),
    [
        (run(make_case("L025"), make_case("L050"), set_sha="6" * 64), "golden set content"),
        (
            run(make_case("L025"), make_case("L050"), generator_version=2),
            "generator version 1 vs 2",
        ),
        (run(make_case("L025", prompt_sha="f" * 64), make_case("L050")), "L025 prompt differs"),
        (run(make_case("L025"), make_case("L050"), model="other"), "--cross-model"),
        (run(make_case("L090")), "no fill level in common"),
    ],
)
def test_different_tests_are_not_comparable(current: Run, reason: str) -> None:
    report = compare_runs(base(), current, T)
    assert report.verdict == "NOT COMPARABLE"
    assert any(reason in r for r in report.reasons)
    assert report.flags == []


def test_cross_model_compares_anyway() -> None:
    current = run(make_case("L025"), make_case("L050"), model="other")
    assert compare_runs(base(), current, T, cross_model=True).verdict == "STABLE"


def test_levels_in_only_one_run_are_listed() -> None:
    report = compare_runs(base(), run(make_case("L025")), T)
    assert report.verdict == "STABLE"
    assert report.not_compared == ["L050"]


def test_lost_needle_is_drift_and_names_the_needle() -> None:
    current = run(make_case("L025"), make_case("L050", missed=("flood-month",)))
    report = compare_runs(base(), current, T)
    assert report.verdict == "DRIFT"
    [flag] = [f for f in report.flags if f.metric == "needle lost"]
    assert (flag.case_id, flag.detail) == ("L050", "flood-month: recall 100% -> 0%")
    assert report.rows[1].lost == ["flood-month"]


def test_gained_needle_is_reported_but_not_drift() -> None:
    baseline = run(make_case("L025", missed=("vault-door",)))
    report = compare_runs(baseline, run(make_case("L025")), T)
    assert report.rows[0].gained == ["vault-door"]
    assert report.verdict == "STABLE"


def test_similarity_fires_just_below_the_threshold_not_at_it() -> None:
    changed = REPLY.replace("heron blue", "a heron-blue shade")
    ratio = similarity(REPLY, changed)
    current = run(make_case("L025", response=changed), make_case("L050"))
    at = compare_runs(base(), current, Thresholds(min_similarity=ratio))
    past = compare_runs(base(), current, Thresholds(min_similarity=ratio + 1e-6))
    assert at.verdict == "STABLE"
    assert past.verdict == "DRIFT"
    assert past.flags[0].metric == "similarity" and f"{ratio:.3f}" in past.flags[0].detail


def test_finish_reason_change_is_drift() -> None:
    current = run(make_case("L025", finish="length"), make_case("L050"))
    report = compare_runs(base(), current, T)
    assert report.verdict == "DRIFT"
    assert report.flags[0].detail == "finish stop -> length"


def test_prompt_token_change_is_an_environment_warning_past_the_threshold() -> None:
    at = run(make_case("L025", reported=1020), make_case("L050"))
    past = run(make_case("L025", reported=1021), make_case("L050"))
    assert compare_runs(base(), at, T).flags == []
    report = compare_runs(base(), past, T)
    assert report.verdict == "STABLE"
    [flag] = report.flags
    assert (flag.kind, flag.metric) == ("environment", "prompt tokens")
    assert "+2.1%" in flag.detail and "2%" in flag.detail


def test_new_truncation_is_an_environment_warning() -> None:
    current = run(make_case("L025", truncation=True), make_case("L050"))
    report = compare_runs(base(), current, T)
    assert [(f.kind, f.metric) for f in report.flags] == [("environment", "truncation")]


def test_errored_case_is_drift() -> None:
    current = run(make_case("L025", error="APITimeoutError: timed out"), make_case("L050"))
    report = compare_runs(base(), current, T)
    assert report.verdict == "DRIFT"
    assert [f.metric for f in report.flags] == ["error"]
    assert "1 of 1 repeats errored" in report.flags[0].detail
    assert report.rows[0].similarity is None


def test_repeats_match_their_best_baseline_reply() -> None:
    other = REPLY.replace("Brumewane", "Brumewane, I believe")
    baseline = run(make_case("L025", response=REPLY), make_case("L025", repeat=2, response=other))
    swapped = run(make_case("L025", response=other), make_case("L025", repeat=2, response=REPLY))
    report = compare_runs(baseline, swapped, T)
    assert report.rows[0].similarity == 1.0
    assert report.rows[0].repeats == {"baseline": 2, "current": 2}


def test_recall_rates_compare_across_repeats() -> None:
    baseline = run(make_case("L025"), make_case("L025", repeat=2, missed=("vault-door",)))
    same_rate = run(make_case("L025", missed=("vault-door",)), make_case("L025", repeat=2))
    lower = run(
        make_case("L025", missed=("vault-door",)),
        make_case("L025", repeat=2, missed=("vault-door",)),
    )
    assert compare_runs(baseline, same_rate, T).rows[0].lost == []
    assert compare_runs(baseline, lower, T).rows[0].lost == ["vault-door"]


def test_metric_deltas() -> None:
    current = run(make_case("L025", latency_ms=1500, reported=1010), make_case("L050"))
    row = compare_runs(base(), current, T).rows[0]
    assert (row.latency_change_pct, row.prompt_tokens_change_pct, row.length_change_pct) == (
        50.0,
        1.0,
        0.0,
    )
