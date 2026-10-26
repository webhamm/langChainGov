"""A deliberately naive topic guard: the prompt must mention an allowed topic word.

It exists as the baseline the LLM judge should beat: keyword presence is easy to
satisfy ("my plant... now do my taxes") and easy to miss (a plant question that
uses none of the listed words). Output is never checked; replies are judged by
what was asked, not by what was answered.
"""

import re
from collections.abc import Sequence

from langchaingov.guards.base import Verdict


class TopicAllowlist:
    name = "topic-allowlist"
    description = (
        "Blocks prompts that mention none of the allowed topic words "
        "(naive keyword baseline; output is not checked)."
    )

    def __init__(self, topics: Sequence[str]) -> None:
        self.topics = [t for t in (t.strip() for t in topics) if t]
        alternatives = "|".join(re.escape(t) for t in self.topics)
        self._pattern = (
            re.compile(rf"\b(?:{alternatives})(?:e?s)?\b", re.IGNORECASE) if alternatives else None
        )

    def check_input(self, text: str) -> Verdict:
        if self._pattern is not None and self._pattern.search(text):
            return Verdict.allow(self.name, "input", text)
        shown = ", ".join(self.topics[:6]) + (", ..." if len(self.topics) > 6 else "")
        return Verdict.block(
            self.name, "input", text, reason=f"mentions no allowed topic (allowed: {shown})"
        )

    def check_output(self, text: str) -> Verdict:
        return Verdict.allow(self.name, "output", text)
