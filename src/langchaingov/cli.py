"""Command-line interface: ``chat``, ``models``, ``version``, and the ``guard`` commands."""

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import openai
import typer
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from rich.console import Console
from rich.table import Table

from langchaingov import __version__
from langchaingov.chain import GuardedChain
from langchaingov.evals.loader import EvalSetError, load_set
from langchaingov.evals.runner import Counts, EvalReport, run_eval
from langchaingov.golden import loader as golden_loader
from langchaingov.golden.compare import DriftReport, Thresholds, compare_runs
from langchaingov.golden.generator import build_payload, usable_tokens
from langchaingov.golden.models import GoldenSet, Payload
from langchaingov.golden.runner import RunRefused, execute_run, plan_run
from langchaingov.golden.store import (
    CaseResult,
    RequestParams,
    RunFileError,
    RunHeader,
    RunSummary,
    RunWriter,
    baseline_key,
    list_runs,
    load_baselines,
    make_run_id,
    pin_baseline,
    read_run,
    run_path,
    set_sha256,
    summarize,
)
from langchaingov.golden.tokens import TiktokenCounter, TokenCounter, TokenizerUnavailable
from langchaingov.guards import registry
from langchaingov.guards.base import GuardedResult, Guardrail, Stage
from langchaingov.guards.middleware import hitl
from langchaingov.llm import list_models, make_chat_model, message_text
from langchaingov.settings import Settings

app = typer.Typer(
    help="LangChain guardrails sandbox talking to a local model through LiteLLM.",
    no_args_is_help=True,
)
guard_app = typer.Typer(help="List and run guardrails.", no_args_is_help=True)
app.add_typer(guard_app, name="guard")
golden_app = typer.Typer(
    help="Golden-set payloads that fill a model's context window, for drift runs.",
    no_args_is_help=True,
)
app.add_typer(golden_app, name="golden")

console = Console()
err_console = Console(stderr=True)

EXIT_ERROR = 1
EXIT_BLOCKED = 2
EXIT_DRIFT = 3
EXIT_CASE_ERRORS = 4

ModelFactory = Callable[[Settings, str | None], BaseChatModel]

# Tests replace these with fakes.
model_factory: ModelFactory = make_chat_model
models_lister: Callable[[Settings], list[str]] = list_models
token_counter_factory: Callable[[], TokenCounter] = TiktokenCounter


def _golden_chat_model(settings: Settings, model: str, params: RequestParams) -> BaseChatModel:
    return make_chat_model(
        settings,
        model,
        max_tokens=params.max_tokens,
        timeout=params.timeout_s,
        seed=params.seed_sent,
        max_retries=params.max_retries,
    )


golden_model_factory: Callable[[Settings, str, RequestParams], BaseChatModel] = _golden_chat_model

JSON_FLAG = typer.Option(False, "--json", help="Print JSON instead of text.")
SYSTEM_OPTION = typer.Option(None, "--system", "-s", help="Optional system prompt.")
MODEL_OPTION = typer.Option(None, "--model", "-m", help="Override LANGCHAINGOV_MODEL.")
GUARD_OPTION = typer.Option(
    ..., "--guard", "-g", help="Guard to apply; repeat to apply several in order."
)


def fail(message: str, code: int = EXIT_ERROR) -> None:
    """Print an error to stderr and exit with ``code``."""
    err_console.print(f"[red]error:[/red] {message}", soft_wrap=True)
    raise typer.Exit(code)


def _require_key(settings: Settings) -> None:
    if not settings.api_key:
        fail("LITELLM_API_KEY is not set. Copy .env.example to .env and fill it in.")


def _configured_model(
    settings: Settings, override: str | None, required: bool = True
) -> tuple[BaseChatModel, str]:
    """Build the chat model. With ``required=False`` missing config is tolerated, for
    commands that only need the model object to construct guards and never call it."""
    model_name = override or settings.model
    if required:
        _require_key(settings)
        if not model_name:
            fail("No model configured. Set LANGCHAINGOV_MODEL in .env or pass --model.")
    return model_factory(settings, model_name), model_name


def _build_guards(names: list[str], settings: Settings, llm: BaseChatModel) -> list[Guardrail]:
    try:
        return [registry.get(name, settings, llm) for name in names]
    except (registry.UnknownGuardError, registry.MissingExtraError) as exc:
        fail(str(exc))
    raise AssertionError("unreachable")


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
    hitl.default_policy = terminal_policy  # lc-hitl asks in the terminal during guard run
    try:
        guards = _build_guards(guard, settings, llm)
    finally:
        hitl.default_policy = None
    chain = GuardedChain(llm, guards, system=system)
    with _client_errors(settings, model_name):
        result = chain.invoke(prompt)

    if json_output:
        console.print_json(json.dumps(_result_payload(result, model_name)))
    else:
        _print_result(result)
    if result.blocked:
        raise typer.Exit(EXIT_BLOCKED)


def terminal_policy(text: str, stage: Stage) -> bool:
    """Human-in-the-loop answer for ``lc-hitl``: ask in the terminal."""
    err_console.print(f"[yellow]lc-hitl[/yellow] review this {stage}:", highlight=False)
    err_console.print(text, markup=False, highlight=False)
    return typer.confirm("Allow it?", default=False, err=True)


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


SET_OPTION = typer.Option(
    None, "--set", help="Eval set YAML file. Default: the packaged houseplant-care set."
)
TAG_OPTION = typer.Option(None, "--tag", "-t", help="Only cases with this tag; repeatable.")
WITH_MODEL_FLAG = typer.Option(
    False, "--with-model", help="Also call the model and run output guards (needs the proxy)."
)


@guard_app.command("eval")
def guard_eval(
    guard: list[str] = GUARD_OPTION,
    set_path: Path | None = SET_OPTION,
    tag: list[str] | None = TAG_OPTION,
    with_model: bool = WITH_MODEL_FLAG,
    system: str | None = SYSTEM_OPTION,
    model: str | None = MODEL_OPTION,
    json_output: bool = JSON_FLAG,
) -> None:
    """Run an eval set through guardrails and count matched, false, and missed blocks.

    By default only input guards run, so no proxy is needed. Exit code 1 only on errors.
    """
    settings = Settings()
    llm, model_name = _configured_model(settings, model, required=with_model)
    guards = _build_guards(guard, settings, llm)
    try:
        eval_set = load_set(set_path)
    except EvalSetError as exc:
        fail(str(exc))

    chain = GuardedChain(llm, guards, system=system)
    with _client_errors(settings, model_name):
        report = run_eval(eval_set, chain, with_model=with_model, tags=tag)

    if json_output:
        payload = {
            **report.model_dump(),
            "totals": report.totals.model_dump(),
            "by_tag": {t: c.model_dump() for t, c in report.by_tag.items()},
        }
        console.print_json(json.dumps(payload))
    else:
        _print_report(report)


def _print_report(report: EvalReport) -> None:
    table = Table("Case", "Tags", "Expected", "Actual", "Match", "Reason")
    for row in report.rows:
        mark = "[green]yes[/green]" if row.matched else "[red]no[/red]"
        table.add_row(row.case_id, ", ".join(row.tags), row.expected, row.actual, mark, row.reason)
    console.print(table)

    summary = Table("Tag", "Cases", "Matched", "False blocks", "Missed blocks")
    for tag, counts in report.by_tag.items():
        summary.add_row(tag, *_count_cells(counts))
    summary.add_row("[bold]all[/bold]", *_count_cells(report.totals))
    console.print(summary)
    mode = "input + model + output" if report.with_model else "input guards only"
    console.print(
        f"Set {report.set_name!r}, guards {', '.join(report.guards)}, mode: {mode}",
        highlight=False,
    )


def _count_cells(counts: Counts) -> list[str]:
    return [
        str(counts.total),
        str(counts.matched),
        str(counts.false_blocks),
        str(counts.missed_blocks),
    ]


GOLDEN_SET_OPTION = typer.Option(
    None, "--set", help="Golden set YAML file. Default: the packaged five-needle set."
)
CONTEXT_OPTION = typer.Option(
    None, "--context", min=1, help="Context window in tokens; overrides the model's profile."
)
LEVEL_OPTION = typer.Option(
    None, "--level", "-l", help="Fill level in (0, 1]; repeatable. Default: the set's ladder."
)
DUMP_OPTION = typer.Option(
    None, "--dump", file_okay=False, help="Also write each prompt to DIR/<case>.txt."
)


@golden_app.command("build")
def golden_build(
    set_path: Path | None = GOLDEN_SET_OPTION,
    model: str | None = MODEL_OPTION,
    context: int | None = CONTEXT_OPTION,
    level: list[float] | None = LEVEL_OPTION,
    dump: Path | None = DUMP_OPTION,
    json_output: bool = JSON_FLAG,
) -> None:
    """Generate the golden-set payloads for a model and print their size and hash.

    Nothing is sent to the model. The same set, model profile, and level always give
    the same SHA-256. Exit code 1 on errors.
    """
    settings = Settings()
    counter = token_counter_factory()
    try:
        golden = golden_loader.load_set(set_path)
        profile = golden_loader.resolve_profile(model or settings.model or None, context)
        levels = level or golden.fill_levels
        payloads = [build_payload(golden, profile, lv, counter) for lv in levels]
        usable = usable_tokens(golden, profile, counter)
    except (golden_loader.GoldenSetError, TokenizerUnavailable) as exc:
        fail(str(exc))

    if dump is not None:
        dump.mkdir(parents=True, exist_ok=True)
        for payload in payloads:
            (dump / f"{payload.case_id}.txt").write_text(payload.prompt, encoding="utf-8")

    if json_output:
        info = {
            "set": golden.name,
            "generator_version": golden.generator_version,
            "seed": golden.seed,
            "model": profile.name,
            "context_tokens": profile.context_tokens,
            "local": profile.local,
            "usable_tokens": usable,
            "counter": counter.name,
            "payloads": [p.model_dump() for p in payloads],
        }
        console.print_json(json.dumps(info))
        return

    _print_payloads(payloads)
    console.print(
        f"Set {golden.name!r} (generator v{golden.generator_version}, seed {golden.seed}), "
        f"model {profile.name} ({'local' if profile.local else 'not local'}): "
        f"{profile.context_tokens} context, {usable} usable after "
        f"{golden.output_reserve_tokens} reserved for the answer and the system prompt, "
        f"counted with {counter.name}",
        highlight=False,
    )
    if dump is not None:
        console.print(f"Prompts written to {dump}/", highlight=False)


def _print_payloads(payloads: list[Payload]) -> None:
    table = Table("Case", "Level", "Target", "Tokens", "Chars", "SHA-256", "Needle depths")
    for p in payloads:
        depths = " ".join(f"{d:.0%}" for d in p.needle_depths.values())
        table.add_row(
            p.case_id,
            f"{p.level:.0%}",
            str(p.target_tokens),
            str(p.est_tokens),
            str(p.chars),
            p.sha256[:12],
            depths,
        )
    console.print(table)


REPEAT_OPTION = typer.Option(1, "--repeat", min=1, help="Send each payload this many times.")
ALLOW_CLOUD_FLAG = typer.Option(
    False, "--allow-cloud", help="Allow a model whose profile is not local (costs money)."
)
MAX_PROMPT_TOKENS_OPTION = typer.Option(
    None,
    "--max-prompt-tokens",
    min=1,
    help="Cloud runs only: most estimated prompt tokens to send. Default: the setting.",
)


@golden_app.command("run")
def golden_run(
    set_path: Path | None = GOLDEN_SET_OPTION,
    model: str | None = MODEL_OPTION,
    context: int | None = CONTEXT_OPTION,
    level: list[float] | None = LEVEL_OPTION,
    repeat: int = REPEAT_OPTION,
    allow_cloud: bool = ALLOW_CLOUD_FLAG,
    max_prompt_tokens: int | None = MAX_PROMPT_TOKENS_OPTION,
    json_output: bool = JSON_FLAG,
) -> None:
    """Send each golden-set payload to the model with fixed parameters and record the replies.

    Writes one JSONL file per run under LANGCHAINGOV_RUNS_DIR. Exit code 0 when every
    case completed, 4 when the run finished but some cases errored, 1 on other errors.
    """
    settings = Settings()
    _require_key(settings)
    model_name = model or settings.model
    if not model_name:
        fail("No model configured. Set LANGCHAINGOV_MODEL in .env or pass --model.")
    counter = token_counter_factory()
    try:
        golden = golden_loader.load_set(set_path)
        profile = golden_loader.resolve_profile(model_name, context)
        levels = level or golden.fill_levels
        cap = max_prompt_tokens or settings.golden_cloud_token_cap
        payloads = plan_run(golden, profile, levels, repeat, counter, allow_cloud, cap)
    except (golden_loader.GoldenSetError, TokenizerUnavailable, RunRefused) as exc:
        fail(str(exc))

    started = datetime.now(UTC)
    params = RequestParams(
        temperature=settings.temperature,
        max_tokens=golden.output_reserve_tokens,
        timeout_s=settings.golden_timeout,
        max_retries=0,
        seed_requested=golden.seed,
        seed_sent=golden.seed if profile.supports_seed else None,
    )
    header = RunHeader(
        run_id=make_run_id(started, model_name),
        started_at=started,
        langchaingov_version=__version__,
        set_name=golden.name,
        set_sha256=set_sha256(golden),
        generator_version=golden.generator_version,
        model=model_name,
        profile=profile,
        params=params,
        counter=counter.name,
        base_url_host=urlparse(settings.base_url).netloc,
        levels=levels,
        repeat=repeat,
    )
    llm = golden_model_factory(settings, model_name, params)
    path = settings.runs_dir / f"{header.run_id}.jsonl"

    def on_start(payload: Payload, index: int) -> None:
        if not json_output:
            err_console.print(
                f"running {payload.case_id} #{index} ({payload.est_tokens} tokens)...",
                highlight=False,
                soft_wrap=True,
            )

    def on_case(result: CaseResult) -> None:
        if not json_output:
            _print_case_line(result)

    with RunWriter(path, header) as writer, _client_errors(settings, model_name):
        results = execute_run(golden, payloads, repeat, llm, writer, on_start, on_case)

    errored = sum(1 for r in results if r.error)
    if json_output:
        summary = {
            "run_id": header.run_id,
            "path": str(path),
            "header": header.model_dump(mode="json"),
            "cases": [r.model_dump(mode="json", exclude={"response"}) for r in results],
            "errored": errored,
        }
        console.print_json(json.dumps(summary))
    else:
        _print_run_summary(golden, results)
        console.print(f"Run {header.run_id} written to {path}", highlight=False, soft_wrap=True)
    if errored:
        raise typer.Exit(EXIT_CASE_ERRORS)


def _print_case_line(r: CaseResult) -> None:
    if r.error:
        console.print(
            f"  {r.case_id} #{r.repeat}: [red]error[/red] {r.error}",
            highlight=False,
            soft_wrap=True,
        )
        return
    flag = " [red]suspected truncation[/red]" if r.suspected_truncation else ""
    console.print(
        f"  {r.case_id} #{r.repeat}: recall {r.recall:.0%}, {r.latency_ms / 1000:.1f} s{flag}",
        highlight=False,
        soft_wrap=True,
    )


def _print_run_summary(golden: GoldenSet, results: list[CaseResult]) -> None:
    table = Table("Case", "Rep", "Est.", "Reported", "Recall", "Finish", "Latency", "Note")
    for r in results:
        if r.error:
            note = f"[red]{r.error}[/red]"
        elif r.suspected_truncation:
            note = "[red]suspected truncation[/red]"
        else:
            missed = [nid for nid, ok in r.needles.items() if not ok]
            note = f"missed: {', '.join(missed)}" if missed else ""
        table.add_row(
            r.case_id,
            str(r.repeat),
            str(r.est_tokens),
            "-" if r.reported_prompt_tokens is None else str(r.reported_prompt_tokens),
            f"{r.recall:.0%}",
            r.finish_reason or "-",
            f"{r.latency_ms / 1000:.1f} s",
            note,
        )
    console.print(table)
    console.print(
        f"Needles: {', '.join(n.id for n in golden.needles)}", highlight=False, soft_wrap=True
    )


@golden_app.command("runs")
def golden_runs(
    model: str | None = typer.Option(None, "--model", "-m", help="Only runs of this model."),
    json_output: bool = JSON_FLAG,
) -> None:
    """List the recorded golden-set runs, oldest first, and which are pinned baselines."""
    settings = Settings()
    try:
        summaries, problems = list_runs(settings.runs_dir)
        pinned = set(load_baselines(settings.runs_dir).values())
    except RunFileError as exc:
        fail(str(exc))
    if model:
        summaries = [s for s in summaries if s.model == model]
    for problem in problems:
        err_console.print(f"[yellow]skipped:[/yellow] {problem}", highlight=False, soft_wrap=True)

    if json_output:
        runs = [{**s.model_dump(mode="json"), "pinned": s.run_id in pinned} for s in summaries]
        payload = {"runs_dir": str(settings.runs_dir), "runs": runs, "unreadable": problems}
        console.print_json(json.dumps(payload))
        return
    if not summaries:
        console.print(
            f"No runs in {settings.runs_dir}. Start one with: langchaingov golden run",
            highlight=False,
            soft_wrap=True,
        )
        return
    _print_runs(summaries, pinned)


def _print_runs(summaries: list[RunSummary], pinned: set[str]) -> None:
    # The run id already says when and which model, and it is what you copy, so it is
    # never wrapped or truncated.
    table = Table()
    table.add_column("Run", no_wrap=True)
    for name in ("Set", "Levels %", "Cases", "Recall", "Status"):
        table.add_column(name, overflow="fold")
    for s in summaries:
        style = {"complete": "green", "errors": "red", "partial": "yellow"}[s.status]
        status = f"[{style}]{s.status}[/{style}]"
        if s.run_id in pinned:
            status += " [bold]baseline[/bold]"
        levels = "/".join(f"{lv * 100:g}" for lv in s.levels)
        table.add_row(
            s.run_id,
            s.set_name,
            levels + (f" x{s.repeat}" if s.repeat > 1 else ""),
            f"{s.cases}/{s.expected_cases}",
            "-" if s.mean_recall is None else f"{s.mean_recall:.0%}",
            status,
        )
    console.print(table)


@golden_app.command("baseline")
def golden_baseline(
    run_id: str | None = typer.Argument(None, help="Run to pin. Omit to list the pins."),
    json_output: bool = JSON_FLAG,
) -> None:
    """Pin a complete run as the baseline for its set and model, or list the pins."""
    settings = Settings()
    runs_dir = settings.runs_dir
    try:
        if run_id:
            path = run_path(runs_dir, run_id)
            summary = summarize(path, *read_run(path))
            pin_baseline(runs_dir, summary)
        pins = load_baselines(runs_dir)
    except RunFileError as exc:
        fail(str(exc))

    if json_output:
        console.print_json(json.dumps({"baselines": pins}))
    elif run_id:
        console.print(
            f"Pinned {run_id} as the baseline for set {summary.set_name!r}, model {summary.model}",
            highlight=False,
            soft_wrap=True,
        )
    elif not pins:
        console.print(
            "No baselines pinned. Pin one with: langchaingov golden baseline <run_id>",
            highlight=False,
            soft_wrap=True,
        )
    else:
        table = Table("Set :: model", "Baseline run")
        for key, value in sorted(pins.items()):
            table.add_row(key, value)
        console.print(table)


@golden_app.command("compare")
def golden_compare(
    run_id: str | None = typer.Argument(
        None, help="Run to check. Default: the latest run of --model / LANGCHAINGOV_MODEL."
    ),
    baseline: str | None = typer.Option(
        None,
        "--baseline",
        help="Run to compare against. Default: the pinned baseline, else the earliest "
        "complete run of the same set and model.",
    ),
    model: str | None = MODEL_OPTION,
    cross_model: bool = typer.Option(
        False, "--cross-model", help="Allow comparing runs of different models."
    ),
    min_similarity: float | None = typer.Option(
        None, "--min-similarity", min=0, max=1, help="Override LANGCHAINGOV_DRIFT_MIN_SIMILARITY."
    ),
    prompt_token_pct: float | None = typer.Option(
        None, "--prompt-token-pct", min=0, help="Override LANGCHAINGOV_DRIFT_PROMPT_TOKEN_PCT."
    ),
    json_output: bool = JSON_FLAG,
) -> None:
    """Compare a run with its baseline, per fill level, and say whether answers drifted.

    Exit code 0 when stable, 3 on drift, 1 when the runs are not comparable or missing.
    """
    settings = Settings()
    runs_dir = settings.runs_dir
    note = ""
    try:
        summaries, _ = list_runs(runs_dir)
        if run_id:
            current_path = run_path(runs_dir, run_id)
        else:
            name = model or settings.model
            candidates = [s for s in summaries if not name or s.model == name]
            if not candidates:
                of_model = f" of {name}" if name else ""
                fail(f"No runs{of_model} in {runs_dir}. Start one with: langchaingov golden run")
            current_path = candidates[-1].path
        current = read_run(current_path)
        head = current[0]

        if baseline:
            baseline_path = run_path(runs_dir, baseline)
        elif pinned := load_baselines(runs_dir).get(baseline_key(head.set_name, head.model)):
            baseline_path = run_path(runs_dir, pinned)
            note = f"Baseline: pinned run {pinned}"
        else:
            complete = [
                s
                for s in summaries
                if s.status == "complete"
                and s.set_name == head.set_name
                and s.model == head.model
                and s.path != current_path
            ]
            if not complete:
                fail(
                    f"No baseline for set {head.set_name!r}, model {head.model}. Pin one with "
                    "langchaingov golden baseline <run_id>, or pass --baseline."
                )
            baseline_path = complete[0].path
            note = (
                f"Baseline: no run pinned for set {head.set_name!r}, model {head.model}; "
                f"using the earliest complete run {complete[0].run_id}"
            )
        if baseline_path == current_path:
            fail(f"{head.run_id} is its own baseline. Record another run, then compare.")
        base = read_run(baseline_path)
    except RunFileError as exc:
        fail(str(exc))

    thresholds = Thresholds(
        min_similarity=settings.drift_min_similarity if min_similarity is None else min_similarity,
        prompt_token_pct=(
            settings.drift_prompt_token_pct if prompt_token_pct is None else prompt_token_pct
        ),
    )
    report = compare_runs(base, current, thresholds, cross_model=cross_model)

    if json_output:
        payload = {**report.model_dump(mode="json"), "note": note}
        payload["thresholds"] = thresholds.model_dump()
        console.print_json(json.dumps(payload))
    else:
        _print_drift(report, note)
    if report.verdict == "NOT COMPARABLE":
        raise typer.Exit(EXIT_ERROR)
    if report.verdict == "DRIFT":
        raise typer.Exit(EXIT_DRIFT)


def _signed(value: float | None) -> str:
    return "-" if value is None else f"{value:+.1f}%"


def _print_drift(report: DriftReport, note: str) -> None:
    if note:
        console.print(note, highlight=False, soft_wrap=True)
    console.print(
        f"Comparing {report.current_run_id} against baseline {report.baseline_run_id}",
        highlight=False,
        soft_wrap=True,
    )
    if report.reasons:
        for reason in report.reasons:
            console.print(f"  - {reason}", highlight=False, soft_wrap=True)
    else:
        table = Table(
            "Case",
            "Recall",
            "Lost / gained",
            "Similarity",
            "Length",
            "Latency",
            "Prompt tok",
            "Finish",
        )
        for row in report.rows:
            changes = " ".join([*(f"-{n}" for n in row.lost), *(f"+{n}" for n in row.gained)])
            finish = "/".join(row.current_finish)
            if row.baseline_finish != row.current_finish:
                finish = f"{'/'.join(row.baseline_finish)} -> {finish}"
            table.add_row(
                row.case_id,
                f"{row.baseline_recall:.0%} -> {row.current_recall:.0%}",
                changes,
                "-" if row.similarity is None else f"{row.similarity:.3f}",
                _signed(row.length_change_pct),
                _signed(row.latency_change_pct),
                _signed(row.prompt_tokens_change_pct),
                finish,
            )
        console.print(table)
        if report.not_compared:
            console.print(
                f"Not compared (only in one run): {', '.join(report.not_compared)}",
                highlight=False,
                soft_wrap=True,
            )
        for flag in report.flags:
            style = "red" if flag.kind == "drift" else "yellow"
            console.print(
                f"  [{style}]{flag.kind}[/{style}] {flag.case_id} {flag.metric}: {flag.detail}",
                highlight=False,
                soft_wrap=True,
            )
    style = {"STABLE": "green", "DRIFT": "red", "NOT COMPARABLE": "yellow"}[report.verdict]
    console.print(f"[bold {style}]{report.verdict}[/bold {style}]")
