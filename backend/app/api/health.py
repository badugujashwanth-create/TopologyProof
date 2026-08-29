"""Health endpoint contract."""

from fastapi import APIRouter

router = APIRouter()
HEALTH_RESPONSE = {"service": "topologyproof", "status": "ok", "version": "0.1.0"}


@router.get("/health")
def get_health() -> dict[str, str]:
    """Return the exact local service health response."""
    return HEALTH_RESPONSE
