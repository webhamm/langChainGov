"""Runtime settings, read from environment variables and an optional ``.env`` file.

All variables use the ``LANGCHAINGOV_`` prefix except the LiteLLM key, which keeps
LiteLLM's own name so one ``.env`` can serve both tools.
"""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Connection settings for the local LiteLLM proxy."""

    model_config = SettingsConfigDict(
        env_prefix="LANGCHAINGOV_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    base_url: str = "http://localhost:4000/v1"
    """OpenAI-compatible endpoint of the LiteLLM proxy."""

    model: str = ""
    """Model name as LiteLLM exposes it. Required for any model call."""

    api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LITELLM_API_KEY", "LITELLM_MASTER_KEY", "LANGCHAINGOV_API_KEY"
        ),
    )
    """API key the LiteLLM proxy expects (its master key works). Required for any model call."""

    temperature: float = 0.0

    blocklist: str = "blorptium,zanthar protocol"
    """Comma-separated words for the ``keyword-blocklist`` guard. Defaults are fictional."""

    def blocklist_words(self) -> list[str]:
        return _split_csv(self.blocklist)

    pii_mode: Literal["redact", "block"] = "redact"
    """What the ``pii-regex`` guard does on a match."""

    topics: str = (
        "plant,houseplant,basil,pothos,monstera,succulent,fern,cactus,cacti,orchid,"
        "fig,leaf,leaves,pot,repot,soil,water,watering,fertilize,fertilizer,"
        "propagate,propagation,cutting,grow light,garden,gardening,nursery"
    )
    """Comma-separated topic words for the ``topic-allowlist`` guard."""

    def topic_words(self) -> list[str]:
        return _split_csv(self.topics)

    judge_model: str = ""
    """Model for the ``llm-judge`` guard. Empty means: reuse the chat model."""

    judge_rubric: Path | None = None
    """Plain-text rubric file for the ``llm-judge`` guard. Empty means: the built-in rubric."""

    hooks_block_phrase: str = "developer mode"
    """``lc-custom-hooks``: a prompt containing this phrase ends the run."""

    hooks_rewrite_from: str = "blorptium"
    hooks_rewrite_to: str = "[a mineral]"
    """``lc-custom-hooks``: this word is rewritten in the reply."""


def _split_csv(value: str) -> list[str]:
    return [w.strip() for w in value.split(",") if w.strip()]
