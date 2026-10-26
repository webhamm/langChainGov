"""The simplest possible guardrail: block text that contains a listed word."""

import re
from collections.abc import Sequence

from langchaingov.guards.base import Stage, Verdict


class KeywordBlocklist:
    name = "keyword-blocklist"
    description = (
        "Blocks input or output containing any listed word (case-insensitive, whole word)."
    )

    def __init__(self, words: Sequence[str]) -> None:
        self.words = [w for w in (w.strip() for w in words) if w]
        alternatives = "|".join(re.escape(w) for w in self.words)
        self._pattern = (
            re.compile(rf"\b(?:{alternatives})\b", re.IGNORECASE) if alternatives else None
        )

    def check_input(self, text: str) -> Verdict:
        return self._check(text, "input")

    def check_output(self, text: str) -> Verdict:
        return self._check(text, "output")

    def _check(self, text: str, stage: Stage) -> Verdict:
        match = self._pattern.search(text) if self._pattern else None
        if match is None:
            return Verdict.allow(self.name, stage, text)
        return Verdict.block(
            self.name, stage, text, reason=f"contains blocked word {match.group(0)!r}"
        )
