"""Command-line interface: ``chat``, ``models``, ``version``, and the ``guard`` commands."""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import openai
import typer
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from rich.console import Console
from rich.table import Table

from langchaingov import __version__
from langchaingov.chain import GuardedChain
from langchaingov.guards import registry
from langchaingov.guards.base import GuardedResult
from langchaingov.llm import list_models, make_chat_model, message_text
from langchaingov.settings import Settings

app = typer.Typer(
    help="LangChain guardrails sandbox talking to a local model through LiteLLM.",
    no_args_is_help=True,
)
guard_app = typer.Typer(help="List and run guardrails.", no_args_is_help=True)
app.add_typer(guard_app, name="guard")

console = Console()
err_console = Console(stderr=True)

EXIT_ERROR = 1
EXIT_BLOCKED = 2

ModelFactory = Callable[[Settings, str | None], BaseChatModel]

# Tests replace these with fakes.
model_factory: ModelFactory = make_chat_model
models_lister: Callable[[Settings], list[str]] = list_models

JSON_FLAG = typer.Option(False, "--json", help="Print JSON instead of text.")
SYSTEM_OPTION = typer.Option(None, "--system", "-s", help="Optional system prompt.")
MODEL_OPTION = typer.Option(None, "--model", "-m", help="Override LANGCHAINGOV_MODEL.")
GUARD_OPTION = typer.Option(
    ..., "--guard", "-g", help="Guard to apply; repeat to apply several in order."
)


def fail(message: str, code: int = EXIT_ERROR) -> None:
    """Print an error to stderr and exit with ``code``."""
    err_console.print(f"[red]error:[/red] {message}")
    raise typer.Exit(code)


def _require_key(settings: Settings) -> None:
    if not settings.api_key:
        fail("LITELLM_API_KEY is not set. Copy .env.example to .env and fill it in.")


def _configured_model(settings: Settings, override: str | None) -> tuple[BaseChatModel, str]:
    _require_key(settings)
    model_name = override or settings.model
    if not model_name:
        fail("No model configured. Set LANGCHAINGOV_MODEL in .env or pass --model.")
    return model_factory(settings, model_name), model_name


@contextmanager
def _client_errors(settings: Settings, model_name: str | None = None) -> Iterator[None]:
    """Turn OpenAI client errors into one-line hints and exit 1."""
    try:
        yield
    except openai.AuthenticationError:
        fail("LiteLLM rejected the API key. Check LITELLM_API_KEY in .env.")
    except openai.NotFoundError:
        fail(f"LiteLLM does not know the model {model_name!r}. Check LANGCHAINGOV_MODEL.")
    except openai.APIConnectionError:
        fail(f"Could not reach LiteLLM at {settings.base_url}. Is the proxy running?")


@app.command()
def version() -> None:
    """Print the package version."""
    console.print(__version__)


@app.command()
def models(json_output: bool = JSON_FLAG) -> None:
    """List the model names the LiteLLM proxy exposes."""
    settings = Settings()
    _require_key(settings)
    with _client_errors(settings):
        names = models_lister(settings)
    if json_output:
        console.print_json(json.dumps({"models": names}))
    else:
        for name in names:
            console.print(name, markup=False, highlight=False)


@app.command()
def chat(
    prompt: str = typer.Argument(..., help="The user message to send."),
    system: str | None = SYSTEM_OPTION,
    model: str | None = MODEL_OPTION,
    json_output: bool = JSON_FLAG,
) -> None:
    """Send one prompt to the local model through LiteLLM and print the reply."""
    settings = Settings()
    llm, model_name = _configured_model(settings, model)
    messages: list[BaseMessage] = []
    if system:
        messages.append(SystemMessage(content=system))
    messages.append(HumanMessage(content=prompt))

    with _client_errors(settings, model_name):
        reply = llm.invoke(messages)

    text = message_text(reply)
    if json_output:
        console.print_json(json.dumps({"model": model_name, "reply": text}))
    else:
        console.print(text, markup=False, highlight=False)


@guard_app.command("list")
def guard_list(json_output: bool = JSON_FLAG) -> None:
    """List the registered guardrails."""
    specs = registry.specs()
    if json_output:
        payload = [{"name": s.name, "description": s.description} for s in specs]
        console.print_json(json.dumps(payload))
        return
    table = Table("Guard", "Description")
    for spec in specs:
        table.add_row(spec.name, spec.description)
    console.print(table)


@guard_app.command("run")
def guard_run(
    prompt: str = typer.Argument(..., help="The user message to send."),
    guard: list[str] = GUARD_OPTION,
    system: str | None = SYSTEM_OPTION,
    model: str | None = MODEL_OPTION,
    json_output: bool = JSON_FLAG,
) -> None:
    """Run a prompt through one or more guardrails and the model.

    Exit code 0 when allowed, 2 when a guard blocked, 1 on errors.
    """
    settings = Settings()
    llm, model_name = _configured_model(settings, model)
    try:
        guards = [registry.get(name, settings, llm) for name in guard]
    except registry.UnknownGuardError as exc:
        fail(str(exc))

    chain = GuardedChain(llm, guards, system=system)
    with _client_errors(settings, model_name):
        result = chain.invoke(prompt)

    if json_output:
        console.print_json(json.dumps(_result_payload(result, model_name)))
    else:
        _print_result(result)
    if result.blocked:
        raise typer.Exit(EXIT_BLOCKED)


def _result_payload(result: GuardedResult, model_name: str) -> dict[str, object]:
    return {
        "model": model_name,
        "blocked": result.blocked,
        "block_reason": result.block_reason,
        **result.model_dump(),
    }


def _print_result(result: GuardedResult) -> None:
    table = Table("Stage", "Guard", "Action", "Reason")
    for v in result.verdicts:
        style = {"allow": "green", "modify": "yellow", "block": "red"}[v.action]
        table.add_row(v.stage, v.guard, f"[{style}]{v.action}[/{style}]", v.reason or "")
    console.print(table)
    if result.blocked:
        console.print(f"[red]Blocked:[/red] {result.block_reason}", highlight=False)
    else:
        console.print(result.reply or "", markup=False, highlight=False)
