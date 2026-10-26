"""Runtime settings, read from environment variables and an optional ``.env`` file.

All variables use the ``LANGCHAINGOV_`` prefix except the LiteLLM key, which keeps
LiteLLM's own name so one ``.env`` can serve both tools.
"""

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
