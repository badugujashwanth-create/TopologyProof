"""Optional provider contract."""
from backend.app.errors import TopologyProofError
from backend.app.schemas.analysis import AssumptionMiningInput, HypothesisBatch


class ProviderUnavailableError(TopologyProofError):
    """Optional provider unavailable."""
class OpenAIProvider:
    """Credential-gated adapter contract."""
    def __init__(self, settings: object) -> None:
        """Store settings."""
        self._settings = settings
    def mine(self, input_data: AssumptionMiningInput) -> HypothesisBatch:
        """Fail safely without network calls."""
        del input_data
        if getattr(self._settings, "openai_api_key", None) is None:
            raise ProviderUnavailableError("missing_openai_configuration")
        raise ProviderUnavailableError("openai_adapter_not_enabled")
