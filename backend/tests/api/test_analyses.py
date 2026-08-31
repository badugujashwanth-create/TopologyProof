"""Real API acceptance proof."""
import time

from fastapi.testclient import TestClient

from backend.app.main import create_app
from demo.webhook_dedup.materialize import materialize_fixture


def test_create_analysis_post_completes_and_publishes(tmp_path):
    """Submit the real fixture and verify published API artifacts."""
    fixture=materialize_fixture(tmp_path/"fixture")
    client=TestClient(create_app())
    response=client.post("/api/v1/analyses",json=fixture.request_json())
    assert response.status_code == 202
    run_id=response.json()["run_id"]
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        status=client.get(f"/api/v1/analyses/{run_id}")
        if status.json().get("status")=="completed": break
        time.sleep(0.05)
    assert status.json()["status"]=="completed"
    findings=client.get(f"/api/v1/analyses/{run_id}/findings")
    assert findings.status_code==200
    assert "high-risk" in findings.text and "review-required" not in findings.text
    trajectory=client.get(f"/api/v1/analyses/{run_id}/trajectory")
    assert trajectory.status_code==200 and trajectory.text
    report=client.get(f"/api/v1/analyses/{run_id}/report")
    assert report.status_code==200
    assert "REVIEW REQUIRED" in report.text and "processed_events" in report.text and "NOT EXECUTED" in report.text

def test_unknown_run_is_404():
    """Unknown run is rejected."""
    assert TestClient(create_app()).get("/api/v1/analyses/UNKNOWN").status_code==404

