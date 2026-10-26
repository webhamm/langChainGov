"""Run every case through a ``GuardedChain`` and count matches."""

from collections import defaultdict

from pydantic import BaseModel, Field

from langchaingov.chain import GuardedChain
from langchaingov.evals.models import EvalCase, EvalSet, Expected
from langchaingov.guards.base import Action, GuardedResult


class EvalRow(BaseModel):
    case_id: str
    tags: list[str]
    expected: Expected
    actual: Action
    matched: bool
    reason: str = ""
    """The first non-allow verdict's reason, so a reader sees what fired."""


class Counts(BaseModel):
    total: int = 0
    matched: int = 0
    false_blocks: int = 0
    """Expected allow, but a guard blocked or modified."""
    missed_blocks: int = 0
    """Expected block, but nothing fired."""

    def add(self, row: EvalRow) -> None:
        self.total += 1
        if row.matched:
            self.matched += 1
        elif row.expected == "allow":
            self.false_blocks += 1
        else:
            self.missed_blocks += 1


class EvalReport(BaseModel):
    set_name: str
    guards: list[str]
    with_model: bool
    rows: list[EvalRow] = Field(default_factory=list)

    @property
    def totals(self) -> Counts:
        counts = Counts()
        for row in self.rows:
            counts.add(row)
        return counts

    @property
    def by_tag(self) -> dict[str, Counts]:
        per_tag: dict[str, Counts] = defaultdict(Counts)
        for row in self.rows:
            for tag in row.tags:
                per_tag[tag].add(row)
        return dict(sorted(per_tag.items()))


def actual_action(result: GuardedResult) -> Action:
    if result.blocked:
        return "block"
    if any(v.action == "modify" for v in result.verdicts):
        return "modify"
    return "allow"


def is_match(expected: Expected, actual: Action) -> bool:
    if expected == "allow":
        return actual == "allow"
    return actual != "allow"


def run_case(case: EvalCase, chain: GuardedChain, with_model: bool) -> EvalRow:
    result = chain.invoke(case.prompt) if with_model else chain.check_prompt(case.prompt)
    actual = actual_action(result)
    reason = next((f"{v.guard} ({v.stage}): {v.reason}" for v in result.verdicts if v.reason), "")
    return EvalRow(
        case_id=case.id,
        tags=case.tags,
        expected=case.expected,
        actual=actual,
        matched=is_match(case.expected, actual),
        reason=reason,
    )


def run_eval(
    eval_set: EvalSet,
    chain: GuardedChain,
    with_model: bool = False,
    tags: list[str] | None = None,
) -> EvalReport:
    report = EvalReport(
        set_name=eval_set.name,
        guards=[g.name for g in chain.guards],
        with_model=with_model,
    )
    for case in eval_set.filtered(tags):
        report.rows.append(run_case(case, chain, with_model))
    return report
