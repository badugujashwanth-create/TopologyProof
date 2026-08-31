"""Finding policy tests."""
from backend.app.findings.verdicts import VerdictPolicy
from backend.app.schemas.common import FindingVerdict, OverallVerdict


def test_static_high_risk_requires_review() -> None:
    """Static high risk is never overall red."""
    class F: verdict=FindingVerdict.HIGH_RISK
    assert VerdictPolicy().overall((F(),)) is OverallVerdict.REVIEW_REQUIRED
