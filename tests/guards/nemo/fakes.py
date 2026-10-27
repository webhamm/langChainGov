"""A fake NeMo ``LLMModel``: answers self-check prompts and intent prompts on command."""

from collections.abc import AsyncIterator
from typing import Any

from nemoguardrails.types import LLMResponse, LLMResponseChunk


class FakeNemoLLM:
    def __init__(
        self,
        block_input: bool = False,
        block_output: bool = False,
        intent: str = "user said something else",
    ) -> None:
        self.block_input = block_input
        self.block_output = block_output
        self.intent = intent
        self.prompts: list[str] = []

    async def generate_async(
        self, prompt: Any, *, stop: list[str] | None = None, **kwargs: Any
    ) -> LLMResponse:
        text = prompt if isinstance(prompt, str) else " ".join(str(m.content) for m in prompt)
        self.prompts.append(text)
        if "Should the user message be blocked" in text:
            return LLMResponse(content="Yes" if self.block_input else "No")
        if "Should the message be blocked" in text:
            return LLMResponse(content="Yes" if self.block_output else "No")
        return LLMResponse(content=self.intent)

    async def stream_async(
        self, prompt: Any, *, stop: list[str] | None = None, **kwargs: Any
    ) -> AsyncIterator[LLMResponseChunk]:
        raise NotImplementedError
        yield  # pragma: no cover

    @property
    def model_name(self) -> str:
        return "fake"

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def provider_url(self) -> None:
        return None
