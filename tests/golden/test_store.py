from datetime import UTC, datetime
from pathlib import Path

import pytest

from langchaingov.golden.loader import load_set
from langchaingov.golden.models import ModelProfile
from langchaingov.golden.store import (
    CaseResult,
    RequestParams,
    RunFileError,
    RunHeader,
    RunWriter,
    make_run_id,
    read_run,
    set_sha256,
)

STARTED = datetime(2026, 11, 19, 15, 30, 5, tzinfo=UTC)


def header() -> RunHeader:
    golden = load_set(None)
    return RunHeader(
        run_id=make_run_id(STARTED, "llama3.2-3b-32k"),
        started_at=STARTED,
        langchaingov_version="0.10.0",
        set_name=golden.name,
        set_sha256=set_sha256(golden),
        generator_version=golden.generator_version,
        model="llama3.2-3b-32k",
        profile=ModelProfile(name="llama3.2-3b-32k", context_tokens=32768, local=True),
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
        levels=[0.25],
        repeat=1,
    )


def case(repeat: int = 1) -> CaseResult:
    return CaseResult(
        case_id="L025",
        level=0.25,
        repeat=repeat,
        target_tokens=100,
        est_tokens=98,
        prompt_sha256="ab" * 32,
        prompt_chars=392,
        reported_prompt_tokens=99,
        completion_tokens=10,
        finish_reason="stop",
        latency_ms=1234,
        response="vault-door: heron blue",
        needles={"vault-door": True},
        recall=1.0,
    )


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("llama3.2-3b-32k", "20261119T153005Z-llama3.2-3b-32k"),
        ("anthropic/Claude Sonnet 5", "20261119T153005Z-anthropic-claude-sonnet-5"),
        ("///", "20261119T153005Z-model"),
    ],
)
def test_run_id_is_sortable_and_file_safe(model: str, expected: str) -> None:
    assert make_run_id(STARTED, model) == expected


def test_set_hash_follows_content_not_formatting() -> None:
    golden = load_set(None)
    assert set_sha256(golden) == set_sha256(load_set(None))
    assert set_sha256(golden) != set_sha256(golden.model_copy(update={"seed": 1}))


def test_writer_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "runs" / "r.jsonl"
    with RunWriter(path, header()) as writer:
        writer.append(case(1))
        writer.append(case(2))
    read_header, cases = read_run(path)
    assert read_header == header()
    assert [c.repeat for c in cases] == [1, 2]
    assert len(path.read_text().splitlines()) == 3


def test_writer_never_overwrites_a_run(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    RunWriter(path, header()).close()
    with pytest.raises(FileExistsError):
        RunWriter(path, header())


def test_each_case_is_on_disk_before_the_run_ends(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    writer = RunWriter(path, header())
    writer.append(case())
    assert len(read_run(path)[1]) == 1  # flushed, not buffered until close
    writer.close()


def test_torn_last_line_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    with RunWriter(path, header()) as writer:
        writer.append(case())
    with path.open("a") as f:
        f.write('{"kind": "case", "case_id": "L0')
    assert len(read_run(path)[1]) == 1


def test_invalid_middle_line_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    path.write_text(header().model_dump_json() + "\nnot json\n" + case().model_dump_json() + "\n")
    with pytest.raises(RunFileError, match="line 2 is invalid"):
        read_run(path)


@pytest.mark.parametrize(
    ("content", "message"), [("", "is empty"), ('{"kind": "case"}\n', "no valid header")]
)
def test_bad_files(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "r.jsonl"
    path.write_text(content)
    with pytest.raises(RunFileError, match=message):
        read_run(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(RunFileError, match="cannot read run file"):
        read_run(tmp_path / "nope.jsonl")
