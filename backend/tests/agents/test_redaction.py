"""Redaction tests."""
from backend.app.agents.assumption_miner.redaction import Redactor


def test_redacts_credentials() -> None:
    """Remove representative credential values."""
    result = Redactor().redact("api_key=abc api-key: abc token=xyz secret:foo password=bar")
    assert result.redacted and all(value not in result.text for value in ("abc", "xyz", "foo", "bar"))

def test_preserves_code() -> None:
    """Preserve ordinary source."""
    assert Redactor().redact("processed_events.add(event_id)").text == "processed_events.add(event_id)"
