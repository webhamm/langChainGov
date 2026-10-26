"""Hand-rolled guardrails with no extra dependencies."""

from langchain_core.language_models import BaseChatModel

from langchaingov import llm
from langchaingov.guards.custom.keyword_blocklist import KeywordBlocklist
from langchaingov.guards.custom.llm_judge import DEFAULT_RUBRIC, LlmJudge
from langchaingov.guards.custom.pii_regex import PiiRegex
from langchaingov.guards.custom.topic_allowlist import TopicAllowlist
from langchaingov.guards.registry import register
from langchaingov.settings import Settings


def make_llm_judge(settings: Settings, model: BaseChatModel) -> LlmJudge:
    judge_model = (
        llm.make_chat_model(settings, settings.judge_model) if settings.judge_model else model
    )
    rubric = (
        settings.judge_rubric.read_text(encoding="utf-8")
        if settings.judge_rubric
        else DEFAULT_RUBRIC
    )
    return LlmJudge(judge_model, rubric)


def register_all() -> None:
    register(
        KeywordBlocklist.name,
        KeywordBlocklist.description,
        lambda settings, model: KeywordBlocklist(settings.blocklist_words()),
    )
    register(
        PiiRegex.name,
        PiiRegex.description,
        lambda settings, model: PiiRegex(settings.pii_mode),
    )
    register(
        TopicAllowlist.name,
        TopicAllowlist.description,
        lambda settings, model: TopicAllowlist(settings.topic_words()),
    )
    register(LlmJudge.name, LlmJudge.description, make_llm_judge)
