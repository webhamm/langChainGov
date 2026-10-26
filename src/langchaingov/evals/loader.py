"""Load an eval set from YAML, or the packaged default."""

from importlib.resources import files
from pathlib import Path

import yaml
from pydantic import ValidationError

from langchaingov.evals.models import EvalSet


class EvalSetError(ValueError):
    """The eval file is missing, unreadable, or does not match the schema."""


def default_set_text() -> str:
    return files("langchaingov.evals.data").joinpath("default.yaml").read_text(encoding="utf-8")


def load_set(path: Path | None) -> EvalSet:
    """Parse ``path``; with ``None``, the packaged default set."""
    if path is None:
        return parse_set(default_set_text(), source="<packaged default>")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EvalSetError(f"cannot read eval set {path}: {exc}") from exc
    return parse_set(text, source=str(path))


def parse_set(text: str, source: str = "<string>") -> EvalSet:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise EvalSetError(f"invalid YAML in {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise EvalSetError(f"{source} must be a mapping with name and cases")
    try:
        return EvalSet.model_validate(data)
    except ValidationError as exc:
        raise EvalSetError(f"invalid eval set {source}: {exc}") from exc
