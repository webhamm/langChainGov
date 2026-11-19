"""The golden runs / baseline / compare commands, on hand-made run files."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from langchaingov import cli
from langchaingov.golden.store import CaseResult
from tests.golden.runs import REPLY, make_case, make_run, write_run

runner = CliRunner()
RUNS = Path("runs/golden")  # the default runs_dir, relative to the per-test temp cwd
FIRST, SECOND, THIRD = "20261119T100000Z-m", "20261119T110000Z-m", "20261119T120000Z-m"


def record(
    run_id: str,
    *cases: CaseResult,
    model: str = "m",
    set_sha: str = "5" * 64,
    context: int = 32768,
) -> None:
    header, chosen = make_run(*cases, run_id=run_id, model=model, set_sha=set_sha, context=context)
    write_run(RUNS, header, chosen)


def invoke(*args: str) -> tuple[int, str]:
    result = runner.invoke(cli.app, ["golden", *args])
    return result.exit_code, result.output


@pytest.fixture
def two_stable_runs() -> None:
    record(FIRST)
    record(SECOND)


def test_runs_with_no_files() -> None:
    code, out = invoke("runs")
    assert code == 0 and "No runs in runs/golden" in out


def test_runs_table_and_json(two_stable_runs: None) -> None:
    code, out = invoke("runs")
    assert code == 0 and FIRST in out and SECOND in out and "complete" in out
    invoke("baseline", FIRST)
    data = json.loads(invoke("runs", "--json")[1])
    assert [(r["run_id"], r["pinned"]) for r in data["runs"]] == [(FIRST, True), (SECOND, False)]


def test_runs_filter_by_model(two_stable_runs: None) -> None:
    record(THIRD, model="other")
    data = json.loads(invoke("runs", "--json", "--model", "other")[1])
    assert [r["run_id"] for r in data["runs"]] == [THIRD]


def test_baseline_pin_and_list(two_stable_runs: None) -> None:
    code, out = invoke("baseline", SECOND)
    assert code == 0 and f"Pinned {SECOND}" in out
    code, out = invoke("baseline")
    assert code == 0 and "default::m" in out and SECOND in out
    assert json.loads(invoke("baseline", "--json")[1]) == {"baselines": {"default::m": SECOND}}


def test_baseline_with_no_pins() -> None:
    code, out = invoke("baseline")
    assert code == 0 and "No baselines pinned" in out


@pytest.mark.parametrize("run_id", ["missing-run", FIRST])
def test_baseline_refuses_missing_or_incomplete_runs(run_id: str) -> None:
    record(FIRST, make_case("L025", error="BadRequestError: nope"))
    code, out = invoke("baseline", run_id)
    assert code == 1 and "error:" in out


def test_compare_falls_back_to_the_earliest_complete_run(
    two_stable_runs: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LANGCHAINGOV_MODEL", "m")
    code, out = invoke("compare")
    assert code == 0, out
    assert f"using the earliest complete run {FIRST}" in out
    assert f"Comparing {SECOND} against baseline {FIRST}" in out
    assert "STABLE" in out


def test_compare_uses_the_pinned_baseline(two_stable_runs: None) -> None:
    record(THIRD)
    invoke("baseline", SECOND)
    code, out = invoke("compare", "--model", "m")
    assert code == 0 and f"pinned run {SECOND}" in out and f"Comparing {THIRD}" in out


def test_compare_drift_exits_3_and_explains(two_stable_runs: None) -> None:
    record(THIRD, make_case("L025"), make_case("L050", missed=("flood-month",)))
    code, out = invoke("compare", THIRD, "--baseline", FIRST)
    assert code == 3
    assert "needle lost: flood-month: recall 100% -> 0%" in out
    assert "DRIFT" in out


def test_compare_not_comparable_exits_1(two_stable_runs: None) -> None:
    record(THIRD, context=65536, set_sha="6" * 64)
    code, out = invoke("compare", THIRD, "--baseline", FIRST)
    assert code == 1 and "NOT COMPARABLE" in out and "golden set content differs" in out


def test_compare_thresholds_can_be_overridden(two_stable_runs: None) -> None:
    changed = REPLY.replace("heron blue", "heron blue (I think)")
    record(THIRD, make_case("L025", response=changed), make_case("L050"))
    assert invoke("compare", THIRD, "--baseline", FIRST)[0] == 0
    code, out = invoke("compare", THIRD, "--baseline", FIRST, "--min-similarity", "0.99")
    assert code == 3 and "< 0.99" in out


def test_compare_json(two_stable_runs: None) -> None:
    code, out = invoke("compare", SECOND, "--baseline", FIRST, "--json")
    data = json.loads(out)
    assert code == 0 and data["verdict"] == "STABLE"
    assert data["thresholds"] == {"min_similarity": 0.9, "prompt_token_pct": 2.0}
    assert [r["case_id"] for r in data["rows"]] == ["L025", "L050"]


def test_compare_picks_the_latest_run_of_the_model(two_stable_runs: None) -> None:
    record(THIRD, model="other")
    code, out = invoke("compare", "--model", "m")
    assert code == 0 and f"Comparing {SECOND}" in out


@pytest.mark.parametrize(
    ("setup", "args", "message"),
    [
        ([], ["compare", "--model", "m"], "No runs of m"),
        ([FIRST], ["compare", "--model", "m"], "No baseline for set"),
        ([FIRST], ["compare", FIRST, "--baseline", FIRST], "is its own baseline"),
        ([FIRST], ["compare", "nope"], "no run 'nope'"),
    ],
)
def test_compare_errors_exit_1(setup: list[str], args: list[str], message: str) -> None:
    for run_id in setup:
        record(run_id)
    code, out = invoke(*args)
    assert code == 1 and message in out
