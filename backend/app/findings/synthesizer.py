"""Finding synthesis."""
from backend.app.schemas.analysis import AssumptionHypothesis
from backend.app.schemas.common import FindingVerdict, Severity, TopologyDimension
from backend.app.schemas.findings import Finding, VerificationRecommendation


class FindingSynthesizer:
    """Convert validated hypotheses into findings."""
    def synthesize(self, snapshot: object, hypotheses: tuple[AssumptionHypothesis, ...] | list[AssumptionHypothesis]) -> tuple[Finding, ...]:
        """Build deterministic findings from provider hypotheses."""
        del snapshot
        findings=[]
        for index, hypothesis in enumerate(hypotheses, 1):
            findings.append(Finding(finding_id=f"TP-{index:03d}", title=hypothesis.engineering_summary, category=TopologyDimension.STATE_LOCALITY, severity=Severity.HIGH, confidence=hypothesis.confidence, deployment_assumption=hypothesis.deployment_assumption, topology_dimensions=hypothesis.topology_dimensions, evidence=hypothesis.evidence, correctness_property=hypothesis.correctness_property, predicted_failure=hypothesis.predicted_failure, verification_recommendation=VerificationRecommendation(worth_running=True, summary=hypothesis.recommendation_summary, topology_dimensions=hypothesis.topology_dimensions, property_assertion=hypothesis.correctness_property), verdict=FindingVerdict.HIGH_RISK, limitations=hypothesis.limitations))
        return tuple(findings)
