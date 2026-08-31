"""Finding, recommendation, and verdict contracts."""

from pydantic import model_validator

from backend.app.schemas.analysis import _require_unique_dimensions
from backend.app.schemas.common import (
    Confidence,
    ContractModel,
    FindingVerdict,
    NonBlankText,
    OverallVerdict,
    Severity,
    TopologyDimension,
)
from backend.app.schemas.evidence import EvidenceLocation, require_unique_evidence

HIGH_CONFIDENCE_THRESHOLD = 0.80


class VerificationRecommendation(ContractModel):
    """Describe a later verification experiment without executing it."""

    worth_running: bool
    summary: NonBlankText
    topology_dimensions: tuple[TopologyDimension, ...]
    property_assertion: NonBlankText

    @model_validator(mode="after")
    def require_unique_dimensions(self) -> "VerificationRecommendation":
        """Require recommendations to name at least one distinct axis."""
        if not self.topology_dimensions:
            raise ValueError("topology_dimensions must not be empty")
        _require_unique_dimensions(self.topology_dimensions)
        return self


class Finding(ContractModel):
    """Represent a checked topology-sensitive correctness finding."""

    finding_id: NonBlankText
    title: NonBlankText
    category: TopologyDimension
    severity: Severity
    confidence: Confidence
    deployment_assumption: NonBlankText
    topology_dimensions: tuple[TopologyDimension, ...]
    evidence: tuple[EvidenceLocation, ...]
    correctness_property: NonBlankText
    predicted_failure: NonBlankText
    verification_recommendation: VerificationRecommendation
    verdict: FindingVerdict
    limitations: tuple[NonBlankText, ...] = ()

    @model_validator(mode="after")
    def require_supported_dimensions_and_evidence(self) -> "Finding":
        """Require findings to retain distinct dimensions and exact support."""
        if not self.topology_dimensions:
            raise ValueError("topology_dimensions must not be empty")
        _require_unique_dimensions(self.topology_dimensions)
        if not self.evidence:
            raise ValueError("evidence must not be empty")
        require_unique_evidence(self.evidence)
        if self.category not in self.topology_dimensions:
            raise ValueError("category must be included in topology_dimensions")
        recommendation_dimensions = set(self.verification_recommendation.topology_dimensions)
        if not recommendation_dimensions.issubset(self.topology_dimensions):
            raise ValueError("recommendation dimensions must be finding dimensions")
        if self.verdict is FindingVerdict.HIGH_RISK:
            if self.severity not in {Severity.CRITICAL, Severity.HIGH}:
                raise ValueError("high-risk findings require critical or high severity")
            if self.confidence < HIGH_CONFIDENCE_THRESHOLD:
                raise ValueError("high-risk findings require high confidence")
        return self


class FindingList(ContractModel):
    """Expose an overall verdict with deterministically ordered findings."""

    overall_verdict: OverallVerdict
    findings: tuple[Finding, ...]

    @model_validator(mode="after")
    def validate_aggregate_verdict(self) -> "FindingList":
        """Require unique IDs and an overall verdict derived from finding verdicts."""
        finding_ids = tuple(finding.finding_id for finding in self.findings)
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("finding_id values must be unique")
        verdicts = {finding.verdict for finding in self.findings}
        if FindingVerdict.HIGH_RISK in verdicts or FindingVerdict.REVIEW_REQUIRED in verdicts:
            expected = OverallVerdict.REVIEW_REQUIRED
        else:
            expected = OverallVerdict.NO_TESTED_TOPOLOGY_FAILURE
        if self.overall_verdict is not expected:
            raise ValueError("overall_verdict does not match finding verdicts")
        return self

