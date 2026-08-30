"""Checked source-location contracts used by analysis evidence."""

from pathlib import PurePosixPath
from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator

from backend.app.schemas.common import ContractModel, NonBlankText, PreservedNonBlankText


def _canonical_posix_path(value: object) -> PurePosixPath:
    """Validate a repository-relative canonical POSIX path."""
    if isinstance(value, PurePosixPath):
        raw_path = value.as_posix()
    elif isinstance(value, str):
        raw_path = value
    else:
        # Pydantic converts ValueError, while TypeError escapes model validation.
        raise ValueError("must be a POSIX path")  # noqa: TRY004
    if not raw_path or raw_path != raw_path.strip():
        raise ValueError("must be a non-empty POSIX path")
    if any(ord(character) < 32 or ord(character) == 127 for character in raw_path):
        raise ValueError("must not contain control characters")
    if "\\" in raw_path:
        raise ValueError("must use POSIX separators")
    path = PurePosixPath(raw_path)
    if path == PurePosixPath(".") or path.is_absolute() or ".." in path.parts:
        raise ValueError("must be a canonical repository-relative path")
    if path.as_posix() != raw_path:
        raise ValueError("must be a canonical repository-relative path")
    return path


CanonicalPosixPath = Annotated[PurePosixPath, BeforeValidator(_canonical_posix_path)]
CommitId = Annotated[str, Field(pattern=r"^[0-9a-f]{40,64}$")]


class EvidenceLocation(ContractModel):
    """Identify source checked against a resolved candidate Git commit."""

    path: CanonicalPosixPath
    line: int = Field(gt=0)
    line_end: int | None = Field(default=None, gt=0)
    symbol: NonBlankText | None = None
    commit_id: CommitId
    excerpt: PreservedNonBlankText

    @model_validator(mode="after")
    def validate_line_range(self) -> "EvidenceLocation":
        """Reject evidence ranges whose end precedes their start."""
        if self.line_end is not None and self.line_end < self.line:
            raise ValueError("line_end must be greater than or equal to line")
        return self


def require_unique_evidence(evidence: tuple[EvidenceLocation, ...]) -> None:
    """Reject repeated source locations within one contract field."""
    if len(evidence) != len(set(evidence)):
        raise ValueError("evidence must be unique")
