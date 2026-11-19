"""Token counters used to size golden-set payloads.

``TiktokenCounter`` is the real one. It is exact for OpenAI models and an approximation
for Llama, which is why every run also records the model's own reported prompt tokens.
tiktoken downloads its encoding on first use (then caches it), so tests use
``CharCounter`` instead.
"""

import math
from typing import Protocol

import tiktoken


class TokenizerUnavailable(RuntimeError):
    """The tokenizer could not be loaded (for example, no network on first use)."""


class TokenCounter(Protocol):
    name: str

    def count(self, text: str) -> int: ...


class CharCounter:
    """Rough rule of thumb: about four characters per token. Offline and instant."""

    name = "chars/4"

    def count(self, text: str) -> int:
        return math.ceil(len(text) / 4)


class TiktokenCounter:
    """Counts with a tiktoken encoding, loaded on first use rather than at construction."""

    def __init__(self, encoding: str = "o200k_base") -> None:
        self.encoding = encoding
        self.name = f"tiktoken:{encoding}"
        self._encoder: tiktoken.Encoding | None = None

    def count(self, text: str) -> int:
        if self._encoder is None:
            try:
                self._encoder = tiktoken.get_encoding(self.encoding)
            except Exception as exc:  # network, cache, or unknown-encoding errors
                raise TokenizerUnavailable(
                    f"tiktoken could not load {self.encoding!r} (it downloads once, then "
                    f"caches): {exc}"
                ) from exc
        return len(self._encoder.encode(text, disallowed_special=()))
