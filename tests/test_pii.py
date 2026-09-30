from app.pii import scrub_text
import pytest


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    assert scrub_text("CCCD: 012345678901") == "CCCD: [REDACTED_CCCD]"


@pytest.mark.parametrize("card", ["4111111111111111", "4111 1111 1111 1111", "4111-1111-1111-1111"])
def test_scrub_credit_card(card: str) -> None:
    assert scrub_text(f"Card: {card}") == "Card: [REDACTED_CREDIT_CARD]"


def test_scrub_event_nested_values() -> None:
    from app.logging_config import scrub_event

    event = {
        "event": "request_failed",
        "exception": "Contact student@example.com",
        "payload": {"items": ["012345678901", {"card": "4111-1111-1111-1111"}]},
        "latency_ms": 123,
        "tool_success": False,
    }
    safe = scrub_event(None, "error", event)
    assert safe["exception"] == "Contact [REDACTED_EMAIL]"
    assert safe["payload"]["items"] == ["[REDACTED_CCCD]", {"card": "[REDACTED_CREDIT_CARD]"}]
    assert safe["latency_ms"] == 123
    assert safe["tool_success"] is False
