"""Verification recommendation boundary tests."""
from backend.app.verification.policy import VerificationPolicy


def test_recommendation_has_no_execution_capability() -> None:
    """Policy contains recommendation only."""
    assert not any(hasattr(VerificationPolicy, name) for name in ("execute", "run", "shell", "subprocess", "docker"))
