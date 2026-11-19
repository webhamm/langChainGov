"""Golden-set run files: one JSONL file per run.

Line 1 is the ``RunHeader``; every later line is one ``CaseResult``, appended and flushed
as soon as the case finishes, so a run that crashes or is interrupted keeps every case
it completed. Prompts are not stored, only their SHA-256: they regenerate from the set.
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
