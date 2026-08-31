"""Offline webhook reasoning."""
from backend.app.schemas.analysis import (
    AssumptionHypothesis,
    AssumptionMiningInput,
    HypothesisBatch,
)
from backend.app.schemas.common import TopologyDimension


class OfflineWebhookProvider:
    """Infer a webhook assumption from complete static facts."""
    def mine(self, input_data: AssumptionMiningInput) -> HypothesisBatch:
        """Return a structured hypothesis only for a supported evidence chain."""
        signal = next((s for s in input_data.static_signals if s.facts.get("correctness_link") and s.facts.get("membership_tested") and s.facts.get("mutation_observed")), None)
        if signal is None:
            return HypothesisBatch(hypotheses=(), limitations=("insufficient_webhook_chain_evidence",))
        return HypothesisBatch(hypotheses=(AssumptionHypothesis(
            hypothesis_id="HYP-OFFLINE-WEBHOOK-001",
            engineering_summary="Process-local webhook deduplication guards a durable payment side effect.",
            correctness_property="One event identifier produces at most one durable payment record.",
            deployment_assumption="Equivalent deliveries observe shared deduplication state across processes.",
            predicted_failure="Duplicate durable payment records when requests reach separate workers.",
            topology_dimensions=(TopologyDimension.REPLICA_COUNT, TopologyDimension.REQUEST_ROUTING, TopologyDimension.STATE_LOCALITY, TopologyDimension.RESTART_RECOVERY),
            evidence=signal.evidence, confidence=0.94,
            recommendation_summary="Send the same event ID to separate workers and compare durable records.",
        ),))
