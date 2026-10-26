"""Hand-rolled guardrails with no extra dependencies."""

from langchaingov.guards.custom.keyword_blocklist import KeywordBlocklist
from langchaingov.guards.registry import register


def register_all() -> None:
    register(
        KeywordBlocklist.name,
        KeywordBlocklist.description,
        lambda settings, model: KeywordBlocklist(settings.blocklist_words()),
    )
