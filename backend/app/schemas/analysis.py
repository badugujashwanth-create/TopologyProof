"""Context, static signal, and provider boundary contracts."""

from pydantic import Field, model_validator

from backend.app.schemas.common import (
    Confidence,
    ContractModel,
    FrozenJsonObject,
    NonBlankText,
    PreservedNonBlankText,
    TopologyDimension,
)
from backend.app.schemas.evidence import (
    CanonicalPosixPath,
    CommitId,
    EvidenceLocation,
    require_unique_evidence,
)
from backend.app.schemas.repository import DiffSummary


def _require_unique_dimensions(dimensions: tuple[TopologyDimension, ...]) -> None:
    """Reject duplicate topology dimensions in a single contract field."""
    if len(dimensions) != len(set(dimensions)):
        raise ValueError("topology_dimensions must be unique")


class ContextItem(ContractModel):
    """Represent one bounded source excerpt selected for analysis context."""

    context_id: NonBlankText
    path: CanonicalPosixPath
    commit: CommitId
    line: int = Field(gt=0)
    line_end: int = Field(gt=0)
    excerpt: PreservedNonBlankText
    symbol: NonBlankText | None = None
    selection_reason: NonBlankText
    provenance: NonBlankText
    redacted: bool = False

    @model_validator(mode="after")
    def validate_line_range(self) -> "ContextItem":
        """Ensure context spans grow forward through source text."""
        if self.line_end < self.line:
            raise ValueError("line_end must be greater than or equal to line")
        return self


class StaticSignal(ContractModel):
    """Record deterministic evidence of a source pattern without a verdict."""

    signal_id: NonBlankText
    kind: NonBlankText
    module: CanonicalPosixPath
    symbol: NonBlankText | None = None
    facts: FrozenJsonObject
    evidence: tuple[EvidenceLocation, ...]
    related_context_ids: tuple[NonBlankText, ...] = ()
    diagnostics: tuple[NonBlankText, ...] = ()
    limitations: tuple[NonBlankText, ...] = ()

    @model_validator(mode="after")
    def require_evidence(self) -> "StaticSignal":
        """Prevent semantic inference from an ungrounded static signal."""
        if not self.evidence:
            raise ValueError("evidence must not be empty")
        require_unique_evidence(self.evidence)
        return self


class AssumptionMiningInput(ContractModel):
    """Bound all provider input to reviewed context and structured facts."""

    ticket: NonBlankText
    diff_summary: DiffSummary
    diff_excerpts: tuple[PreservedNonBlankText, ...]
    context_items: tuple[ContextItem, ...]
    static_signals: tuple[StaticSignal, ...]
    test_context: tuple[NonBlankText, ...] = ()
    deployment_context: tuple[NonBlankText, ...] = ()
    limitations: tuple[NonBlankText, ...] = ()


class AssumptionHypothesis(ContractModel):
    """Represent a provider-proposed topology-sensitive correctness concern."""

    hypothesis_id: NonBlankText
    engineering_summary: NonBlankText
    correctness_property: NonBlankText
    deployment_assumption: NonBlankText
    predicted_failure: NonBlankText
    topology_dimensions: tuple[TopologyDimension, ...]
    evidence: tuple[EvidenceLocation, ...]
    confidence: Confidence
    recommendation_summary: NonBlankText
    limitations: tuple[NonBlankText, ...] = ()

    @model_validator(mode="after")
    def require_supported_dimensions_and_evidence(self) -> "AssumptionHypothesis":
        """Require a hypothesis to retain distinct dimensions and exact support."""
        if not self.topology_dimensions:
            raise ValueError("topology_dimensions must not be empty")
        _require_unique_dimensions(self.topology_dimensions)
        if not self.evidence:
            raise ValueError("evidence must not be empty")
        require_unique_evidence(self.evidence)
        return self


class HypothesisBatch(ContractModel):
    """Return validated provider hypotheses with explicit provider limitations."""

    hypotheses: tuple[AssumptionHypothesis, ...]
    limitations: tuple[NonBlankText, ...] = ()
