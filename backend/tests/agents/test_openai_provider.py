"""Optional provider tests."""
import pytest

from backend.app.agents.assumption_miner.openai_provider import (
    OpenAIProvider,
    ProviderUnavailableError,
)
from backend.app.config import Settings


def test_missing_key_fails_typed() -> None:
    """No credentials produce a safe typed error."""
    with pytest.raises(ProviderUnavailableError, match="missing_openai_configuration"):
        OpenAIProvider(Settings()).mine(None)  # type: ignore[arg-type]
