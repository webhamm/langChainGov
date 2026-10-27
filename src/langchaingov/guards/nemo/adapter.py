"""Run NeMo Guardrails Colang 2 rails through the ``Guardrail`` protocol.

The rails config (``rails/``) has no ``llm continuation``: the sandbox's chain calls the
model, so NeMo only decides. Two mechanisms:

- ``check_input`` sends the prompt through ``LLMRails.generate``. The input rails run the
  self-check prompt; a block comes back as an ``InputRailException`` event. The intent
  flows then map the prompt onto a defined user intent, and an off-topic intent triggers
  the canned refusal, which is read back as a block.
- ``check_output`` sends a custom ``CheckReply`` event through ``process_events``; the
  ``check bot reply`` flow runs the output rails on it, and a block comes back as an
  ``OutputRailException`` event.
"""

import asyncio
from importlib.resources import files
from typing import Any

import yaml
from nemoguardrails import LLMRails, RailsConfig

from langchaingov.guards.base import Verdict
from langchaingov.settings import Settings

REFUSAL = "Sorry, I only help with houseplants, plant care, and gardening."
"""Must match ``bot refuse off topic`` in ``rails/rails.co``."""


def rails_dir() -> Any:
    return files("langchaingov.guards.nemo.rails")


def build_config(settings: Settings) -> RailsConfig:
    """The packaged Colang and YAML, with the model entry rendered from settings."""
    raw = yaml.safe_load(rails_dir().joinpath("config.yml").read_text(encoding="utf-8"))
    raw["models"] = [
        {
            "type": "main",
            "engine": "openai",
            "model": settings.model or "unset",
            "parameters": {
                "base_url": settings.base_url,
                "api_key": settings.api_key or "unset",
            },
        }
    ]
    colang = rails_dir().joinpath("rails.co").read_text(encoding="utf-8")
    return RailsConfig.from_content(colang_content=colang, yaml_content=yaml.safe_dump(raw))


class NemoRailsGuard:
    name = "nemo-rails"
    description = "NeMo Guardrails Colang 2 rails"

    def __init__(self, rails: LLMRails) -> None:
        self.rails = rails

    @classmethod
    def from_settings(cls, settings: Settings, llm: Any = None) -> "NemoRailsGuard":
        """``llm`` overrides the configured model (tests pass a fake ``LLMModel``)."""
        return cls(LLMRails(build_config(settings), llm=llm))

    def check_input(self, text: str) -> Verdict:
        out = self.rails.generate(messages=[{"role": "user", "content": text}])
        response: dict[str, Any] = out if isinstance(out, dict) else {}
        blocked = _exception_message(response.get("events", []), "InputRailException")
        if blocked:
            return Verdict.block(self.name, "input", text, reason=f"self check input: {blocked}")
        content = str(response.get("content") or "")
        if content.strip() == REFUSAL:
            return Verdict.block(
                self.name, "input", text, reason="off-topic: a Colang intent flow refused"
            )
        return Verdict.allow(self.name, "input", text)

    def check_output(self, text: str) -> Verdict:
        events = [{"type": "CheckReply", "text": text}]
        out_events, _state = asyncio.run(self.rails.process_events_async(events, state=None))
        blocked = _exception_message(out_events, "OutputRailException")
        if blocked:
            return Verdict.block(self.name, "output", text, reason=f"self check output: {blocked}")
        return Verdict.allow(self.name, "output", text)


def _exception_message(events: list[dict[str, Any]], kind: str) -> str | None:
    for event in events:
        if event.get("type") == kind:
            return str(event.get("message") or kind)
    return None
