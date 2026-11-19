"""Run listing and baseline pins in golden/store.py."""

from pathlib import Path

import pytest

from langchaingov.golden.store import (
    RunFileError,
    list_runs,
    load_baselines,
    pin_baseline,
    run_path,
)
from tests.golden.runs import make_case, make_header, write_run


def three_runs(runs_dir: Path) -> None:
    write_run(runs_dir, make_header("20261119T120000Z-m"), [make_case("L025"), make_case("L050")])
    write_run(  # interrupted after one case
        runs_dir, make_header("20261119T100000Z-m"), [make_case("L025")]
    )
    write_run(
        runs_dir,
        make_header("20261119T110000Z-m"),
        [make_case("L025"), make_case("L050", error="BadRequestError: too long")],
    )


def test_runs_are_listed_oldest_first_with_status(tmp_path: Path) -> None:
    three_runs(tmp_path)
    summaries, problems = list_runs(tmp_path)
    assert problems == []
    assert [(s.run_id[9:15], s.status) for s in summaries] == [
        ("100000", "partial"),
        ("110000", "errors"),
        ("120000", "complete"),
    ]
    assert summaries[0].cases == 1 and summaries[0].expected_cases == 2
    assert summaries[1].errored == 1 and summaries[1].mean_recall == 1.0


def test_unreadable_files_are_reported_not_fatal(tmp_path: Path) -> None:
    three_runs(tmp_path)
    (tmp_path / "junk.jsonl").write_text("not json\n")
    summaries, problems = list_runs(tmp_path)
    assert len(summaries) == 3
    assert len(problems) == 1 and "junk.jsonl" in problems[0]


def test_missing_dir_lists_nothing(tmp_path: Path) -> None:
    assert list_runs(tmp_path / "nope") == ([], [])


def test_pin_a_complete_run(tmp_path: Path) -> None:
    three_runs(tmp_path)
    summaries, _ = list_runs(tmp_path)
    pin_baseline(tmp_path, summaries[2])
    assert load_baselines(tmp_path) == {"default::m": "20261119T120000Z-m"}


@pytest.mark.parametrize("index", [0, 1], ids=["partial", "errors"])
def test_only_complete_runs_can_be_pinned(tmp_path: Path, index: int) -> None:
    three_runs(tmp_path)
    summary = list_runs(tmp_path)[0][index]
    with pytest.raises(RunFileError, match="only a complete run"):
        pin_baseline(tmp_path, summary)
    assert load_baselines(tmp_path) == {}


def test_bad_baselines_file(tmp_path: Path) -> None:
    (tmp_path / "baselines.json").write_text("[1, 2]")
    with pytest.raises(RunFileError, match="must map"):
        load_baselines(tmp_path)


def test_run_path_names_the_fix(tmp_path: Path) -> None:
    with pytest.raises(RunFileError, match="golden runs"):
        run_path(tmp_path, "nope")
