"""Shared fixtures for backend tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create an API client with isolated artifact storage."""
    settings = Settings(artifact_root=tmp_path / "runs")
    return TestClient(create_app(settings))
