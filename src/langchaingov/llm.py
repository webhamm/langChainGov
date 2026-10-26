"""The one place that knows how to build a chat model for the LiteLLM proxy."""

import openai
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from langchaingov.settings import Settings


def make_chat_model(settings: Settings, model: str | None = None) -> BaseChatModel:
    """Return a ``ChatOpenAI`` pointed at the LiteLLM proxy described by ``settings``.

    ``model`` overrides ``settings.model`` when given. No network call is made here;
    the client connects lazily on first invocation. An empty key is replaced by a
    placeholder so the client can be built for offline use; the proxy rejects it on use.
    """
    return ChatOpenAI(
        base_url=settings.base_url,
        api_key=SecretStr(settings.api_key or "unset"),
        model=model or settings.model,
        temperature=settings.temperature,
    )


def list_models(settings: Settings) -> list[str]:
    """Return the model names the LiteLLM proxy exposes at ``/v1/models``."""
    client = openai.OpenAI(base_url=settings.base_url, api_key=settings.api_key)
    return sorted(model.id for model in client.models.list())


def message_text(message: BaseMessage) -> str:
    """Flatten a message's content to plain text (content may be a list of blocks)."""
    content = message.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            parts.append(block["text"])
    return "".join(parts)
