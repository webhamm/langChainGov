"""Load a golden set and resolve a model profile."""

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from langchaingov.golden.models import GoldenSet, ModelProfile


class GoldenSetError(ValueError):
    """A golden set or profile is missing, invalid, or does not fit the model."""


def default_set_text() -> str:
    return files("langchaingov.golden.data").joinpath("default.yaml").read_text(encoding="utf-8")


def load_set(path: Path | None) -> GoldenSet:
    """Parse ``path``; with ``None``, the packaged default set."""
    if path is None:
        return parse_set(default_set_text(), source="<packaged default>")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GoldenSetError(f"cannot read golden set {path}: {exc}") from exc
    return parse_set(text, source=str(path))


def parse_set(text: str, source: str = "<string>") -> GoldenSet:
    data = _mapping(text, source)
    try:
        return GoldenSet.model_validate(data)
    except ValidationError as exc:
        raise GoldenSetError(f"invalid golden set {source}: {exc}") from exc


def load_profiles(text: str | None = None) -> dict[str, ModelProfile]:
    """Profiles keyed by LiteLLM model name; with ``None``, the packaged ``models.yaml``."""
    source = "models.yaml"
    if text is None:
        text = files("langchaingov.golden").joinpath("models.yaml").read_text(encoding="utf-8")
    models = _mapping(text, source).get("models")
    if not isinstance(models, dict):
        raise GoldenSetError(f"{source} must have a 'models' mapping")
    try:
        return {
            name: ModelProfile.model_validate({"name": name, **fields})
            for name, fields in models.items()
        }
    except (ValidationError, TypeError) as exc:
        raise GoldenSetError(f"invalid model profile in {source}: {exc}") from exc


def resolve_profile(
    model: str | None,
    context: int | None,
    profiles: dict[str, ModelProfile] | None = None,
) -> ModelProfile:
    """The profile for ``model``. ``context`` overrides only the window of a known profile
    (its other flags are kept); a model without a profile needs it and counts as not local."""
    profiles = load_profiles() if profiles is None else profiles
    known = profiles.get(model) if model else None
    if context is not None:
        if known is not None:
            return known.model_copy(update={"context_tokens": context})
        return ModelProfile(name=model or "custom", context_tokens=context)
    if known is not None:
        return known
    if not model:
        raise GoldenSetError(
            "No model given. Pass --model, set LANGCHAINGOV_MODEL, or pass --context N."
        )
    names = ", ".join(sorted(profiles)) or "none"
    raise GoldenSetError(
        f"No profile for model {model!r} (known: {names}). Pass --context N with the window "
        "it is served with, or add it to src/langchaingov/golden/models.yaml."
    )


def _mapping(text: str, source: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise GoldenSetError(f"invalid YAML in {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise GoldenSetError(f"{source} must be a mapping")
    return data
