"""Regex-based detection of a few PII shapes, with redaction or blocking."""

import re
from typing import Literal

from langchaingov.guards.base import Stage, Verdict

PiiMode = Literal["redact", "block"]

# Order matters: card numbers before phones (a card contains phone-shaped digit runs),
# SSNs before phones for the same reason.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("CARD", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\d)")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
]


class PiiRegex:
    name = "pii-regex"
    description = (
        "Finds emails, phone numbers, SSN- and card-shaped numbers with regexes; "
        "redacts them (default) or blocks."
    )

    def __init__(self, mode: PiiMode = "redact") -> None:
        self.mode: PiiMode = mode

    def check_input(self, text: str) -> Verdict:
        return self._check(text, "input")

    def check_output(self, text: str) -> Verdict:
        return self._check(text, "output")

    def _check(self, text: str, stage: Stage) -> Verdict:
        found: list[str] = []
        redacted = text
        for label, pattern in PATTERNS:
            redacted, count = pattern.subn(f"[{label}]", redacted)
            if count:
                found.append(f"{label.lower()} x{count}")
        if not found:
            return Verdict.allow(self.name, stage, text)
        summary = ", ".join(found)
        if self.mode == "block":
            return Verdict.block(self.name, stage, text, reason=f"contains PII: {summary}")
        return Verdict.modify(self.name, stage, redacted, reason=f"redacted PII: {summary}")
