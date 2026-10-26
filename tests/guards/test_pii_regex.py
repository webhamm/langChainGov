import pytest

from langchaingov.guards.custom.pii_regex import PiiRegex


@pytest.fixture
def redactor() -> PiiRegex:
    return PiiRegex()


def test_redacts_email(redactor: PiiRegex) -> None:
    v = redactor.check_input("Write to jane.doe@example.com please")
    assert v.action == "modify"
    assert v.text == "Write to [EMAIL] please"
    assert v.reason == "redacted PII: email x1"


def test_redacts_phone_variants(redactor: PiiRegex) -> None:
    v = redactor.check_input("Call (555) 014-2778 or 555.014.2778 or +1 555-014-2778.")
    assert v.text == "Call [PHONE] or [PHONE] or [PHONE]."
    assert v.reason == "redacted PII: phone x3"


def test_redacts_ssn_and_card_without_phone_confusion(redactor: PiiRegex) -> None:
    v = redactor.check_output("SSN 123-45-6789 and card 4111 1111 1111 1111 on file.")
    assert v.stage == "output"
    assert v.text == "SSN [SSN] and card [CARD] on file."
    assert v.reason == "redacted PII: card x1, ssn x1"


def test_mixed_kinds_summary(redactor: PiiRegex) -> None:
    v = redactor.check_input("sam.lee@example.org, 555-014-2778, 123-45-6789")
    assert v.text == "[EMAIL], [PHONE], [SSN]"
    assert v.reason == "redacted PII: ssn x1, phone x1, email x1"


def test_clean_text_allowed(redactor: PiiRegex) -> None:
    v = redactor.check_input("My pothos has 12 leaves and I water it every 7 days since 2024.")
    assert v.action == "allow"
    assert v.text.endswith("since 2024.")


def test_block_mode() -> None:
    v = PiiRegex(mode="block").check_input("mail me at jane.doe@example.com")
    assert v.action == "block"
    assert v.reason == "contains PII: email x1"
    assert v.text == "mail me at jane.doe@example.com"
