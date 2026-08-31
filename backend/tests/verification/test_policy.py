"""Verification policy tests."""
from backend.app.verification.policy import VerificationPolicy


def test_policy_is_recommendation_only() -> None:
    """Policy exposes no execution methods."""
    assert not hasattr(VerificationPolicy, "execute")
