"""Finding synthesis boundary tests."""
from backend.app.findings.verdicts import VerdictPolicy
from backend.app.schemas.common import FindingVerdict, OverallVerdict


def test_webhook_high_risk_requires_review_without_runtime() -> None:
    """Static high risk is review-required overall."""
    class Finding: verdict = FindingVerdict.HIGH_RISK
    assert VerdictPolicy().finding_verdict(Finding()) is FindingVerdict.HIGH_RISK
    assert VerdictPolicy().overall((Finding(),), runtime=None) is OverallVerdict.REVIEW_REQUIRED
