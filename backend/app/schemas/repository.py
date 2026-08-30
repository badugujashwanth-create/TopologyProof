"""Repository request, snapshot, diff, and changed-symbol contracts."""

from collections.abc import Mapping
from pathlib import Path
from typing import Self

from pydantic import Field, ValidationInfo, field_validator, model_validator

from backend.app.config import DEFAULT_MAX_TICKET_CHARACTERS, ProviderName, Settings
from backend.app.schemas.common import ContractModel, NonBlankText
from backend.app.schemas.evidence import CanonicalPosixPath, CommitId


class RepositoryRefRequest(ContractModel):
    """Describe a local repository and two refs selected for comparison."""

    repo_path: Path
    base_ref: NonBlankText
    candidate_ref: NonBlankText
    provider: ProviderName = ProviderName.OFFLINE

    @field_validator("repo_path")
    @classmethod
    def require_absolute_path(cls, value: Path) -> Path:
        """Reject repository paths that do not remain local and explicit."""
        if not value.is_absolute():
            raise ValueError("repo_path must be absolute")
        return value


class AnalysisRequest(RepositoryRefRequest):
    """Add a bounded, user-supplied correctness requirement to a ref request."""

    ticket: NonBlankText

    @field_validator("ticket")
    @classmethod
    def enforce_ticket_limit(cls, value: str, info: ValidationInfo) -> str:
        """Enforce the injected application ticket limit or its stable default."""
        limit = DEFAULT_MAX_TICKET_CHARACTERS
        if isinstance(info.context, dict):
            configured_limit = info.context.get("max_ticket_characters")
            if isinstance(configured_limit, int):
                limit = configured_limit
        if len(value) > limit:
            raise ValueError(f"ticket must contain at most {limit} characters")
        return value

    @classmethod
    def model_validate_with_settings(
        cls, data: Mapping[str, object], settings: Settings
    ) -> Self:
        """Validate a request using configured provider and ticket defaults."""
        payload = dict(data)
        payload.setdefault("provider", settings.provider)
        return cls.model_validate(
            payload,
            context={"max_ticket_characters": settings.max_ticket_characters},
        )


class RepositorySnapshot(ContractModel):
    """Describe the canonical repository state resolved by intake."""

    repository_root: Path
    base_commit: CommitId
    candidate_commit: CommitId
    repository_id: NonBlankText

    @field_validator("repository_root")
    @classmethod
    def require_canonical_root(cls, value: Path) -> Path:
        """Require an absolute resolved root for all downstream reads."""
        if not value.is_absolute():
            raise ValueError("repository_root must be absolute")
        if value != value.resolve(strict=False):
            raise ValueError("repository_root must be canonical and resolved")
        return value


class ChangedPath(ContractModel):
    """Describe one changed repository-relative path in a diff."""

    path: CanonicalPosixPath
    change_type: NonBlankText
    old_path: CanonicalPosixPath | None = None


class DiffSummary(ContractModel):
    """Summarize a bounded diff without retaining its source text."""

    changed_file_count: int = Field(ge=0)
    changed_python_file_count: int = Field(ge=0)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_file_counts(self) -> "DiffSummary":
        """Reject language-specific counts larger than the total file count."""
        if self.changed_python_file_count > self.changed_file_count:
            raise ValueError("changed_python_file_count cannot exceed changed_file_count")
        return self


class DiffArtifact(ContractModel):
    """Carry a bounded patch and parsed change metadata through analysis."""

    patch: str
    changed_paths: tuple[ChangedPath, ...]
    summary: DiffSummary
    diagnostics: tuple[NonBlankText, ...] = ()

    @model_validator(mode="after")
    def validate_summary_counts(self) -> "DiffArtifact":
        """Require summary file counts to match the parsed changed paths."""
        if self.summary.changed_file_count != len(self.changed_paths):
            raise ValueError("changed_file_count must match changed_paths")
        python_file_count = sum(path.path.suffix == ".py" for path in self.changed_paths)
        if self.summary.changed_python_file_count != python_file_count:
            raise ValueError("changed_python_file_count must match changed_paths")
        return self


class ChangedSymbol(ContractModel):
    """Describe a symbol touched by a candidate-commit diff."""

    path: CanonicalPosixPath
    kind: NonBlankText
    name: NonBlankText
    candidate_commit: CommitId
    old_line_start: int | None = Field(default=None, gt=0)
    old_line_end: int | None = Field(default=None, gt=0)
    new_line_start: int | None = Field(default=None, gt=0)
    new_line_end: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_line_spans(self) -> "ChangedSymbol":
        """Require at least one complete, forward old or new source span."""
        spans = (
            ("old", self.old_line_start, self.old_line_end),
            ("new", self.new_line_start, self.new_line_end),
        )
        if all(start is None and end is None for _, start, end in spans):
            raise ValueError("at least one old or new line span is required")
        for label, start, end in spans:
            if (start is None) != (end is None):
                raise ValueError(f"{label} line span requires both start and end")
            if start is not None and end is not None and end < start:
                raise ValueError(f"{label}_line_end must be greater than or equal to start")
        return self
