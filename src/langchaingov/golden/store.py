"""Golden-set run files: one JSONL file per run, plus ``baselines.json``.

Line 1 is the ``RunHeader``; every later line is one ``CaseResult``, appended and flushed
as soon as the case finishes, so a run that crashes or is interrupted keeps every case
it completed. Prompts are not stored, only their SHA-256: they regenerate from the set.
``baselines.json`` in the same directory maps "set::model" to the pinned run id.
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import IO, Literal, Self

from pydantic import BaseModel, ValidationError

from langchaingov.golden.models import GoldenSet, ModelProfile


class RunFileError(ValueError):
    """A run file is missing or has no valid header."""


class RequestParams(BaseModel):
    temperature: float
    max_tokens: int
    timeout_s: float
    max_retries: int
    seed_requested: int
    seed_sent: int | None
    """``None`` when the profile does not say the provider honours a seed."""


class RunHeader(BaseModel):
    kind: Literal["run"] = "run"
    run_id: str
    started_at: datetime
    langchaingov_version: str
    set_name: str
    set_sha256: str
    generator_version: int
    model: str
    profile: ModelProfile
    params: RequestParams
    counter: str
    base_url_host: str
    levels: list[float]
    repeat: int


class CaseResult(BaseModel):
    kind: Literal["case"] = "case"
    case_id: str
    level: float
    repeat: int
    """1-based repeat index within the run."""
    target_tokens: int
    est_tokens: int
    prompt_sha256: str
    prompt_chars: int
    reported_prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    latency_ms: int
    response: str = ""
    needles: dict[str, bool]
    recall: float
    suspected_truncation: bool = False
    error: str | None = None


def set_sha256(golden: GoldenSet) -> str:
    """Hash of the set's content (not its YAML formatting), so comments never matter."""
    canonical = json.dumps(golden.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def make_run_id(started: datetime, model: str) -> str:
    slug = re.sub(r"[^a-z0-9.]+", "-", model.casefold()).strip("-") or "model"
    return f"{started:%Y%m%dT%H%M%SZ}-{slug}"


class RunWriter:
    """Writes the header on open and appends one flushed line per case."""

    def __init__(self, path: Path, header: RunHeader) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._file: IO[str] = path.open("x", encoding="utf-8")
        self._write(header)

    def append(self, case: CaseResult) -> None:
        self._write(case)

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _write(self, record: BaseModel) -> None:
        self._file.write(record.model_dump_json() + "\n")
        self._file.flush()


def read_run(path: Path) -> tuple[RunHeader, list[CaseResult]]:
    """The header and every complete case. A torn last line (the process died mid-write)
    is skipped; any other invalid line is an error."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RunFileError(f"cannot read run file {path}: {exc}") from exc
    if not lines:
        raise RunFileError(f"run file {path} is empty")
    try:
        header = RunHeader.model_validate_json(lines[0])
    except ValidationError as exc:
        raise RunFileError(f"run file {path} has no valid header: {exc}") from exc
    cases: list[CaseResult] = []
    for number, line in enumerate(lines[1:], start=2):
        try:
            cases.append(CaseResult.model_validate_json(line))
        except ValidationError as exc:
            if number == len(lines):
                break
            raise RunFileError(f"run file {path} line {number} is invalid: {exc}") from exc
    return header, cases


RunStatus = Literal["complete", "errors", "partial"]
BASELINES_FILE = "baselines.json"


class RunSummary(BaseModel):
    run_id: str
    path: Path
    started_at: datetime
    model: str
    set_name: str
    levels: list[float]
    repeat: int
    cases: int
    expected_cases: int
    errored: int
    mean_recall: float | None
    status: RunStatus
    """``partial``: cases are missing (interrupted); ``errors``: all there, some errored."""


def summarize(path: Path, header: RunHeader, cases: list[CaseResult]) -> RunSummary:
    expected = len(header.levels) * header.repeat
    errored = sum(1 for c in cases if c.error)
    status: RunStatus = "partial" if len(cases) < expected else "errors" if errored else "complete"
    scored = [c.recall for c in cases if not c.error]
    return RunSummary(
        run_id=header.run_id,
        path=path,
        started_at=header.started_at,
        model=header.model,
        set_name=header.set_name,
        levels=header.levels,
        repeat=header.repeat,
        cases=len(cases),
        expected_cases=expected,
        errored=errored,
        mean_recall=sum(scored) / len(scored) if scored else None,
        status=status,
    )


def list_runs(runs_dir: Path) -> tuple[list[RunSummary], list[str]]:
    """Every readable run, oldest first (run ids sort by time), and one message per file
    that could not be read."""
    summaries: list[RunSummary] = []
    problems: list[str] = []
    for path in sorted(runs_dir.glob("*.jsonl")) if runs_dir.is_dir() else []:
        try:
            summaries.append(summarize(path, *read_run(path)))
        except RunFileError as exc:
            problems.append(str(exc))
    summaries.sort(key=lambda s: s.run_id)
    return summaries, problems


def run_path(runs_dir: Path, run_id: str) -> Path:
    path = runs_dir / f"{run_id}.jsonl"
    if not path.is_file():
        raise RunFileError(f"no run {run_id!r} in {runs_dir} (see: langchaingov golden runs)")
    return path


def baseline_key(set_name: str, model: str) -> str:
    return f"{set_name}::{model}"


def load_baselines(runs_dir: Path) -> dict[str, str]:
    path = runs_dir / BASELINES_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunFileError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        raise RunFileError(f"{path} must map 'set::model' to a run id")
    return data


def pin_baseline(runs_dir: Path, summary: RunSummary) -> None:
    """Pin a complete run as the baseline for its set and model."""
    if summary.status != "complete":
        raise RunFileError(
            f"run {summary.run_id} is {summary.status}; only a complete run can be a baseline"
        )
    pins = load_baselines(runs_dir)
    pins[baseline_key(summary.set_name, summary.model)] = summary.run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / BASELINES_FILE).write_text(
        json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
