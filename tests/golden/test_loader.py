from pathlib import Path

import pytest

from langchaingov.golden.loader import (
    GoldenSetError,
    load_profiles,
    load_set,
    parse_set,
    resolve_profile,
)
from langchaingov.golden.models import ModelProfile

ROOT = Path(__file__).resolve().parents[2]


def test_default_set_has_five_needles_on_the_resolved_ladder() -> None:
    golden = load_set(None)
    assert [n.depth for n in golden.needles] == [0.05, 0.25, 0.5, 0.75, 0.95]
    assert golden.fill_levels == [0.25, 0.5, 0.75, 0.9]
    assert golden.output_reserve_tokens == 1024


def test_missing_file_is_a_one_line_error(tmp_path: Path) -> None:
    with pytest.raises(GoldenSetError, match="cannot read golden set"):
        load_set(tmp_path / "nope.yaml")


@pytest.mark.parametrize(
    ("text", "message"),
    [("name: [unclosed", "invalid YAML"), ("- a list", "must be a mapping"), ("name: x", "seed")],
)
def test_bad_set_text(text: str, message: str) -> None:
    with pytest.raises(GoldenSetError, match=message):
        parse_set(text)


def test_packaged_profile_matches_the_served_window() -> None:
    profile = load_profiles()["llama3.2-3b-32k"]
    assert profile.local
    modelfile = (ROOT / "infra" / "ollama" / "llama3.2-3b-32k.Modelfile").read_text()
    assert f"PARAMETER num_ctx {profile.context_tokens}" in modelfile


def test_profiles_must_be_a_mapping() -> None:
    with pytest.raises(GoldenSetError, match="'models' mapping"):
        load_profiles("models: [a, b]")
    with pytest.raises(GoldenSetError, match="invalid model profile"):
        load_profiles("models:\n  m:\n    context_tokens: -1\n")


PROFILES = {"local-m": ModelProfile(name="local-m", context_tokens=8000, local=True)}


def test_known_model_resolves_to_its_profile() -> None:
    assert resolve_profile("local-m", None, PROFILES).context_tokens == 8000


def test_context_overrides_the_window_but_keeps_the_local_flag() -> None:
    profile = resolve_profile("local-m", 4000, PROFILES)
    assert (profile.context_tokens, profile.local) == (4000, True)


def test_unknown_model_with_context_is_not_local() -> None:
    profile = resolve_profile("cloud-m", 100_000, PROFILES)
    assert (profile.name, profile.local) == ("cloud-m", False)


def test_unknown_model_without_context_names_the_fix() -> None:
    with pytest.raises(GoldenSetError, match=r"known: local-m.*--context N"):
        resolve_profile("cloud-m", None, PROFILES)


def test_no_model_and_no_context() -> None:
    with pytest.raises(GoldenSetError, match="No model given"):
        resolve_profile(None, None, PROFILES)
