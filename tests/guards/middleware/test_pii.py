from langchaingov.guards.middleware.pii import LangChainPii


def test_redacts_builtin_and_custom_types() -> None:
    v = LangChainPii().check_input(
        "Mail jane.doe@example.com, call (555) 014-2778, SSN 123-45-6789, see https://example.com"
    )
    assert v.action == "modify"
    assert "[REDACTED_EMAIL]" in v.text
    assert "[REDACTED_PHONE]" in v.text
    assert "[REDACTED_SSN]" in v.text
    assert "[REDACTED_URL]" in v.text
    assert "jane.doe" not in v.text and "2778" not in v.text
    assert v.reason.startswith("rewritten by PIIMiddleware[")


def test_clean_text_allowed() -> None:
    v = LangChainPii().check_input("My monstera has 9 leaves.")
    assert v.action == "allow"


def test_output_is_checked_too() -> None:
    v = LangChainPii().check_output("Card 4111 1111 1111 1111 is on file.")
    assert v.stage == "output" and v.action == "modify"
    assert "[REDACTED_CREDIT_CARD]" in v.text


def test_block_strategy() -> None:
    v = LangChainPii(strategy="block").check_input("mail jane.doe@example.com")
    assert v.action == "block"
    assert v.reason.startswith("PIIMiddleware[email]: Detected 1 instance(s) of email")
