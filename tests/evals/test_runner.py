from langchaingov.chain import GuardedChain
from langchaingov.evals.loader import parse_set
from langchaingov.evals.runner import actual_action, is_match, run_eval
from langchaingov.guards.base import GuardedResult, Verdict
from langchaingov.guards.custom.keyword_blocklist import KeywordBlocklist
from tests.fakes import RaisingChatModel, RecordingChatModel, StubGuard

SET = """
name: counts
cases:
  - id: clean-allow
    prompt: tell me about ferns
    expected: allow
    tags: [benign]
  - id: clean-but-blocked
    prompt: tell me about cacti
    expected: allow
    tags: [benign, tricky]
  - id: bad-caught
    prompt: tell me about blorptium
    expected: block
    tags: [jailbreak]
  - id: bad-missed
    prompt: do something sneaky
    expected: block
    tags: [jailbreak]
"""


def test_counts_match_hand_computation() -> None:
    eval_set = parse_set(SET)
    guard = KeywordBlocklist(["blorptium", "cacti"])
    model = RaisingChatModel(responses=["x"], error=AssertionError("model must not be called"))
    report = run_eval(eval_set, GuardedChain(model, [guard]))

    assert report.guards == ["keyword-blocklist"]
    assert report.with_model is False
    assert [(r.case_id, r.actual, r.matched) for r in report.rows] == [
        ("clean-allow", "allow", True),
        ("clean-but-blocked", "block", False),
        ("bad-caught", "block", True),
        ("bad-missed", "allow", False),
    ]
    totals = report.totals
    assert (totals.total, totals.matched, totals.false_blocks, totals.missed_blocks) == (
        4,
        2,
        1,
        1,
    )
    by_tag = report.by_tag
    assert list(by_tag) == ["benign", "jailbreak", "tricky"]
    assert (by_tag["benign"].matched, by_tag["benign"].false_blocks) == (1, 1)
    assert (by_tag["jailbreak"].matched, by_tag["jailbreak"].missed_blocks) == (1, 1)
    assert report.rows[1].reason == "keyword-blocklist (input): contains blocked word 'cacti'"


def test_tag_filter() -> None:
    eval_set = parse_set(SET)
    model = RecordingChatModel(responses=["ok"])
    report = run_eval(eval_set, GuardedChain(model, [StubGuard()]), tags=["tricky"])
    assert [r.case_id for r in report.rows] == ["clean-but-blocked"]


def test_with_model_runs_output_guards() -> None:
    eval_set = parse_set(SET)
    model = RecordingChatModel(responses=["reply mentions blorptium"] * 4)
    guard = KeywordBlocklist(["blorptium"])
    report = run_eval(eval_set, GuardedChain(model, [guard]), with_model=True)
    assert report.with_model is True
    # The input guard lets "clean-allow" through, but the reply trips the output guard.
    row = report.rows[0]
    assert row.actual == "block" and row.matched is False
    assert row.reason.startswith("keyword-blocklist (output)")
    # One model call per case that passed the input guard (3 of 4).
    assert len(model.seen) == 3


def test_modify_counts_as_caught() -> None:
    eval_set = parse_set(SET)
    model = RecordingChatModel(responses=["ok"])
    guard = StubGuard("redactor", on_input=("modify", "redacted"))
    report = run_eval(eval_set, GuardedChain(model, [guard]))
    assert all(r.actual == "modify" for r in report.rows)
    assert [r.matched for r in report.rows] == [False, False, True, True]
    assert report.totals.false_blocks == 2


def test_actual_action_and_is_match() -> None:
    allow = GuardedResult(prompt="p", reply="r", verdicts=[Verdict.allow("g", "input", "p")])
    modify = GuardedResult(
        prompt="p", reply="r", verdicts=[Verdict.modify("g", "input", "P", "up")]
    )
    assert actual_action(allow) == "allow"
    assert actual_action(modify) == "modify"
    assert is_match("allow", "allow") and not is_match("allow", "modify")
    assert is_match("block", "modify") and not is_match("block", "allow")
