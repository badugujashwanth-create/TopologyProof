"""Offline vertical-slice proof."""
import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app
from demo.webhook_dedup.materialize import materialize_fixture


def test_offline_fixture_vertical_slice(tmp_path: Path) -> None:
    """Submit real fixture and inspect actual artifacts."""
    fixture=materialize_fixture(tmp_path/"fixture"); client=TestClient(create_app()); response=client.post("/api/v1/analyses",json=fixture.request_json()); assert response.status_code==202; run_id=response.json()["run_id"]; deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        status=client.get(f"/api/v1/analyses/{run_id}")
        if status.json().get("status")=="completed": break
        time.sleep(.05)
    assert status.json()["status"]=="completed"; findings=client.get(f"/api/v1/analyses/{run_id}/findings"); report=client.get(f"/api/v1/analyses/{run_id}/report"); trajectory=client.get(f"/api/v1/analyses/{run_id}/trajectory")
    assert findings.status_code==200 and "high-risk" in findings.text; assert report.status_code==200 and "processed_events" in report.text and "REVIEW REQUIRED" in report.text and "NOT EXECUTED" in report.text; assert trajectory.status_code==200 and trajectory.text

