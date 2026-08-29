"""Tests for the M0 application foundation."""

from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from backend.app.config import ProviderName, Settings


def test_settings_default_to_offline_and_loopback(tmp_path: Path) -> None:
    """Use safe offline defaults for a local installation."""
    settings = Settings(artifact_root=tmp_path / "runs")

    assert settings.provider == ProviderName.OFFLINE
    assert settings.api_host == "127.0.0.1"
    assert settings.openai_api_key is None


@pytest.mark.parametrize(
    "setting_name",
    [
        "git_command_timeout_seconds",
        "max_diff_bytes",
        "max_source_file_bytes",
        "max_changed_files",
        "max_context_files",
        "max_ticket_characters",
    ],
)
def test_settings_reject_invalid_named_limits(
    tmp_path: Path, setting_name: str
) -> None:
    """Reject non-positive values for every named execution limit."""
    with pytest.raises(ValueError):
        Settings.model_validate(
            {"artifact_root": tmp_path / "runs", setting_name: 0}
        )


def test_settings_normalize_blank_openai_values(tmp_path: Path) -> None:
    """Normalize blank live-provider configuration without exposing secrets."""
    settings = Settings(
        artifact_root=tmp_path / "runs",
        openai_api_key=cast(SecretStr, "   "),
        openai_model="\t",
    )

    assert settings.openai_api_key is None
    assert settings.openai_model is None


def test_settings_parse_prefixed_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Load recognized settings through the configured environment prefix."""
    monkeypatch.setenv("TOPOLOGYPROOF_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TOPOLOGYPROOF_MAX_CHANGED_FILES", "42")
    settings = Settings()

    assert isinstance(settings.openai_api_key, SecretStr)
    assert settings.openai_api_key.get_secret_value() == "test-key"
    assert settings.max_changed_files == 42


def test_settings_forbid_unknown_constructor_values() -> None:
    """Reject configuration fields outside the approved settings contract."""
    with pytest.raises(ValueError):
        Settings.model_validate({"unapproved_setting": True})


@pytest.mark.parametrize(
    ("setting_name", "expected"),
    [
        ("git_command_timeout_seconds", 30),
        ("max_diff_bytes", 5_000_000),
        ("max_source_file_bytes", 1_000_000),
        ("max_changed_files", 500),
        ("max_context_files", 50),
        ("max_ticket_characters", 20_000),
    ],
)
def test_settings_use_approved_named_limit_defaults(
    tmp_path: Path, setting_name: str, expected: int
) -> None:
    """Preserve every approved M1 input limit at its documented default."""
    settings = Settings(artifact_root=tmp_path / "runs")

    assert getattr(settings, setting_name) == expected


def test_health_returns_service_version(client: TestClient) -> None:
    """Expose the exact local service health contract."""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "topologyproof",
        "status": "ok",
        "version": "0.1.0",
    }
