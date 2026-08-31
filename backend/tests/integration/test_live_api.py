"""Loopback HTTP smoke."""
import subprocess
import time
from pathlib import Path

import httpx

from demo.webhook_dedup.materialize import materialize_fixture


def test_live_uvicorn_http(tmp_path: Path) -> None:
    """Prove a real Uvicorn process completes the offline pipeline."""
    fixture = materialize_fixture(tmp_path / "fixture")
    process = subprocess.Popen([r".venv\Scripts\python.exe", "-m", "uvicorn", "backend.app.main:create_app", "--factory", "--host", "127.0.0.1", "--port", "8765"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with httpx.Client(base_url="http://127.0.0.1:8765") as client:
            for _ in range(50):
                try:
                    if client.get("/api/v1/health").status_code == 200: break
                except httpx.HTTPError: pass
                time.sleep(0.1)
            else: raise AssertionError("server not ready")
            response = client.post("/api/v1/analyses", json=fixture.request_json())
            assert response.status_code == 202
            run_id = response.json()["run_id"]
            for _ in range(100):
                status = client.get(f"/api/v1/analyses/{run_id}")
                if status.json().get("status") == "completed": break
                time.sleep(0.05)
            assert status.json()["status"] == "completed"
            assert client.get(f"/api/v1/analyses/{run_id}/findings").status_code == 200
            trajectory = client.get(f"/api/v1/analyses/{run_id}/trajectory")
            assert trajectory.status_code == 200 and trajectory.text
            report = client.get(f"/api/v1/analyses/{run_id}/report")
            assert report.status_code == 200 and all(value in report.text for value in ("processed_events", "REVIEW REQUIRED", "NOT EXECUTED"))
    finally:
        process.terminate(); process.wait(timeout=5)
