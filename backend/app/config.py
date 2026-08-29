"""Configuration for the local TopologyProof service."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_ARTIFACT_ROOT = Path(".topologyproof") / "runs"
DEFAULT_APP_NAME = "TopologyProof"
DEFAULT_APP_VERSION = "0.1.0"
DEFAULT_GIT_COMMAND_TIMEOUT_SECONDS = 30
DEFAULT_MAX_DIFF_BYTES = 5_000_000
DEFAULT_MAX_SOURCE_FILE_BYTES = 1_000_000
DEFAULT_MAX_CHANGED_FILES = 500
DEFAULT_MAX_CONTEXT_FILES = 50
DEFAULT_MAX_TICKET_CHARACTERS = 20_000


class ProviderName(StrEnum):
    """Supported assumption-mining providers."""

    OFFLINE = "offline"
    OPENAI = "openai"


class Settings(BaseSettings):
    """Validated application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="TOPOLOGYPROOF_", env_file=".env", extra="forbid"
    )

    app_name: str = DEFAULT_APP_NAME
    app_version: str = DEFAULT_APP_VERSION
    provider: ProviderName = ProviderName.OFFLINE
    api_host: str = DEFAULT_API_HOST
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )
    git_command_timeout_seconds: int = Field(default=DEFAULT_GIT_COMMAND_TIMEOUT_SECONDS, gt=0)
    max_diff_bytes: int = Field(default=DEFAULT_MAX_DIFF_BYTES, gt=0)
    max_source_file_bytes: int = Field(default=DEFAULT_MAX_SOURCE_FILE_BYTES, gt=0)
    max_changed_files: int = Field(default=DEFAULT_MAX_CHANGED_FILES, gt=0)
    max_context_files: int = Field(default=DEFAULT_MAX_CONTEXT_FILES, gt=0)
    max_ticket_characters: int = Field(default=DEFAULT_MAX_TICKET_CHARACTERS, gt=0)

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def normalize_openai_api_key(cls, value: object) -> object:
        """Normalize blank OpenAI API keys to absent secrets."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("openai_model", mode="before")
    @classmethod
    def normalize_openai_model(cls, value: object) -> object:
        """Normalize blank OpenAI models to absent configuration."""
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached validated application settings."""
    return Settings()
