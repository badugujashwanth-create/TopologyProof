from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_unknown_run_404():
    assert TestClient(create_app()).get("/api/v1/analyses/UNKNOWN/findings").status_code in (404,409)
