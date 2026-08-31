"""Typed provider boundary and deterministic fake."""
from typing import Protocol

from backend.app.config import ProviderName
from backend.app.schemas.analysis import AssumptionMiningInput, HypothesisBatch


class AssumptionProvider(Protocol):
    """Define provider interface."""
    def mine(self, input_data: AssumptionMiningInput) -> HypothesisBatch:
        """Produce structured hypotheses."""
        ...

class FakeAssumptionProvider:
    """Return an injected deterministic batch."""
    def __init__(self, batch: HypothesisBatch) -> None:
        """Store batch."""
        self._batch = batch
    def mine(self, input_data: AssumptionMiningInput) -> HypothesisBatch:
        """Return batch."""
        del input_data
        return self._batch

class ProviderRegistry:
    """Resolve configured providers."""
    def __init__(self, providers: dict[ProviderName, AssumptionProvider]) -> None:
        """Store providers."""
        self._providers = providers
    def get(self, name: ProviderName) -> AssumptionProvider:
        """Get provider or fail."""
        if name not in self._providers:
            raise ValueError("provider_unavailable")
        return self._providers[name]
