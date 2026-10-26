"""LangChain's built-in ``PIIMiddleware`` as a guardrail.

One ``PIIMiddleware`` instance handles one PII type. The built-in detectors cover
email, credit cards, IPs, MAC addresses and URLs; phone numbers and SSNs reuse the
regexes from the custom ``pii-regex`` guard through the ``detector`` hook, which is how
you teach the middleware a new type.
"""

import re
from collections.abc import Callable
from typing import Literal

from langchain.agents.middleware import PIIDetectionError, PIIMatch, PIIMiddleware

from langchaingov.guards.custom.pii_regex import PATTERNS
from langchaingov.guards.middleware.adapter import Middleware, MiddlewareGuard

Strategy = Literal["redact", "block"]

_BUILTIN_TYPES = ("email", "credit_card", "url")
_CUSTOM_TYPES = {"phone": "PHONE", "ssn": "SSN"}


def regex_detector(pattern: re.Pattern[str], pii_type: str) -> Callable[[str], list[PIIMatch]]:
    def detect(text: str) -> list[PIIMatch]:
        return [
            PIIMatch(type=pii_type, value=m.group(0), start=m.start(), end=m.end())
            for m in pattern.finditer(text)
        ]

    return detect


def make_pii_middlewares(strategy: Strategy) -> list[Middleware]:
    middlewares: list[Middleware] = [
        PIIMiddleware(pii_type, strategy=strategy, apply_to_output=True)
        for pii_type in _BUILTIN_TYPES
    ]
    patterns = dict(PATTERNS)
    for pii_type, label in _CUSTOM_TYPES.items():
        middlewares.append(
            PIIMiddleware(
                pii_type,
                strategy=strategy,
                detector=regex_detector(patterns[label], pii_type),
                apply_to_output=True,
            )
        )
    return middlewares


class LangChainPii(MiddlewareGuard):
    name = "lc-pii"
    description = (
        "LangChain PIIMiddleware for email, credit card, URL (built-in) plus phone and "
        "SSN (custom detectors); redacts or blocks on input and output."
    )

    def __init__(self, strategy: Strategy = "redact") -> None:
        super().__init__(
            self.name,
            self.description,
            make_pii_middlewares(strategy),
            block_on=(PIIDetectionError,),
        )
