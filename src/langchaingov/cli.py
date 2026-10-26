"""Command-line interface: ``langchaingov chat``, ``models``, and ``version``."""

import json
from collections.abc import Callable

import openai
import typer
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from rich.console import Console

from langchaingov import __version__
from langchaingov.llm import list_models, make_chat_model
from langchaingov.settings import Settings

app = typer.Typer(
    help="LangChain guardrails sandbox talking to a local model through LiteLLM.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)

ModelFactory = Callable[[Settings, str | None], BaseChatModel]

# Tests replace these with fakes.
model_factory: ModelFactory = make_chat_model
models_lister: Callable[[Settings], list[str]] = list_models


def fail(message: str, code: int = 1) -> None:
    """Print an error to stderr and exit with ``code``."""
    err_console.print(f"[red]error:[/red] {message}")
    raise typer.Exit(code)


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


@app.command()
def version() -> None:
    """Print the package version."""
    console.print(__version__)


@app.command()
def models(
    json_output: bool = typer.Option(False, "--json", help="Print JSON instead of text."),
) -> None:
    """List the model names the LiteLLM proxy exposes."""
    settings = Settings()
    if not settings.api_key:
        fail("LITELLM_API_KEY is not set. Copy .env.example to .env and fill it in.")
    try:
        names = models_lister(settings)
    except openai.AuthenticationError:
        fail("LiteLLM rejected the API key. Check LITELLM_API_KEY in .env.")
    except openai.APIConnectionError:
        fail(f"Could not reach LiteLLM at {settings.base_url}. Is the proxy running?")
    if json_output:
        console.print_json(json.dumps({"models": names}))
    else:
        for name in names:
            console.print(name, markup=False, highlight=False)


@app.command()
def chat(
    prompt: str = typer.Argument(..., help="The user message to send."),
    system: str | None = typer.Option(None, "--system", "-s", help="Optional system prompt."),
    model: str | None = typer.Option(None, "--model", "-m", help="Override LANGCHAINGOV_MODEL."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON instead of text."),
) -> None:
    """Send one prompt to the local model through LiteLLM and print the reply."""
    settings = Settings()
    if not settings.api_key:
        fail("LITELLM_API_KEY is not set. Copy .env.example to .env and fill it in.")
    model_name = model or settings.model
    if not model_name:
        fail("No model configured. Set LANGCHAINGOV_MODEL in .env or pass --model.")

    llm = model_factory(settings, model_name)
    messages: list[BaseMessage] = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))

    try:
        reply = llm.invoke(messages)
    except openai.AuthenticationError:
        fail("LiteLLM rejected the API key. Check LITELLM_API_KEY in .env.")
    except openai.NotFoundError:
        fail(f"LiteLLM does not know the model {model_name!r}. Check LANGCHAINGOV_MODEL.")
    except openai.APIConnectionError:
        fail(f"Could not reach LiteLLM at {settings.base_url}. Is the proxy running?")

    text = message_text(reply)
    if json_output:
        console.print_json(json.dumps({"model": model_name, "reply": text}))
    else:
        console.print(text, markup=False, highlight=False)
