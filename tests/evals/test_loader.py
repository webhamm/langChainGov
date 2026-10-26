from pathlib import Path

import pytest

from langchaingov.evals.loader import EvalSetError, load_set, parse_set

VALID = """
name: tiny
cases:
  - id: a
    prompt: hello
    expected: allow
    tags: [benign]
  - id: b
    prompt: bad thing
    expected: block
"""


def test_packaged_default_set_loads() -> None:
    eval_set = load_set(None)
    assert eval_set.name == "default"
    assert len(eval_set.cases) >= 20
    tags = {t for c in eval_set.cases for t in c.tags}
    assert {"benign", "jailbreak", "pii", "off-topic", "toxic"} <= tags
    assert all(c.expected == "allow" for c in eval_set.cases if "benign" in c.tags)
    assert all(c.expected == "block" for c in eval_set.cases if "benign" not in c.tags)


def test_load_from_file(tmp_path: Path) -> None:
    path = tmp_path / "tiny.yaml"
    path.write_text(VALID)
    eval_set = load_set(path)
    assert [c.id for c in eval_set.cases] == ["a", "b"]
    assert eval_set.cases[1].tags == []


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(EvalSetError, match="cannot read eval set"):
        load_set(tmp_path / "nope.yaml")


def test_invalid_yaml() -> None:
    with pytest.raises(EvalSetError, match="invalid YAML"):
        parse_set("name: [unclosed")


def test_not_a_mapping() -> None:
    with pytest.raises(EvalSetError, match="must be a mapping"):
        parse_set("- just\n- a list\n")


def test_missing_field() -> None:
    with pytest.raises(EvalSetError, match="invalid eval set"):
        parse_set("name: x\ncases:\n  - id: a\n    prompt: hi\n")


def test_bad_expected_value() -> None:
    with pytest.raises(EvalSetError, match="expected"):
        parse_set("name: x\ncases:\n  - id: a\n    prompt: hi\n    expected: maybe\n")


def test_duplicate_ids() -> None:
    text = "name: x\ncases:\n" + "  - id: a\n    prompt: hi\n    expected: allow\n" * 2
    with pytest.raises(EvalSetError, match="duplicate case id 'a'"):
        parse_set(text)


def test_filtered_by_tag() -> None:
    eval_set = parse_set(VALID)
    assert [c.id for c in eval_set.filtered(["benign"])] == ["a"]
    assert [c.id for c in eval_set.filtered(None)] == ["a", "b"]
    assert eval_set.filtered(["nothing"]) == []
