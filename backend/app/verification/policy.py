"""Verification recommendation policy."""
from backend.app.schemas.findings import Finding, VerificationRecommendation


class VerificationPolicy:
    """Create recommendation data without execution capability."""
    def recommend(self, finding: Finding) -> VerificationRecommendation:
        """Return a future experiment recommendation."""
        return finding.verification_recommendation
