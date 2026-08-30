"""Resolve local repositories and build bounded diff artifacts."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath

from pydantic import field_validator, model_validator

from backend.app.config import Settings
from backend.app.errors import TopologyProofError
from backend.app.ingestion.git_client import GitClient
from backend.app.schemas.common import ContractModel, NonBlankText
from backend.app.schemas.evidence import CommitId
from backend.app.schemas.repository import (
    AnalysisRequest,
    ChangedPath,
    DiffArtifact,
    DiffSummary,
    RepositoryRefRequest,
    RepositorySnapshot,
)

DIFF_SECTION_PREFIX = "diff --git "
OLD_PATH_PREFIX = "--- "
NEW_PATH_PREFIX = "+++ "
HUNK_PREFIX = "@@ "
GIT_OLD_PATH_PREFIX = "a/"
GIT_NEW_PATH_PREFIX = "b/"
NULL_DIFF_PATH = "/dev/null"


class RepositoryIntakeError(TopologyProofError):
    """Describe a safe repository-intake failure."""


class AnalysisPreview(ContractModel):
    """Expose bounded repository and diff metadata without semantic analysis."""

    repository_root: Path
    base_commit: CommitId
    candidate_commit: CommitId
    repository_id: NonBlankText
    changed_paths: tuple[ChangedPath, ...]
    summary: DiffSummary
    diagnostics: tuple[NonBlankText, ...] = ()

    @field_validator("repository_root")
    @classmethod
    def require_canonical_root(cls, value: Path) -> Path:
        """Require the preview to retain an absolute canonical repository root."""
        if not value.is_absolute() or value != value.resolve(strict=False):
            raise ValueError("repository_root must be canonical and resolved")
        return value

    @model_validator(mode="after")
    def require_matching_file_count(self) -> AnalysisPreview:
        """Keep preview paths and summary counts internally consistent."""
        if len(self.changed_paths) != self.summary.changed_file_count:
            raise ValueError("changed_file_count must match changed_paths")
        return self


class RepositoryIntake:
    """Resolve repository requests through the bounded read-only Git client."""

    def __init__(self, settings: Settings) -> None:
        """Bind intake limits and Git execution settings."""
        self._settings = settings

    def resolve(self, request: AnalysisRequest) -> RepositorySnapshot:
        """Resolve an analysis request into immutable repository coordinates."""
        return self._resolve_refs(request)

    def load_diff(self, snapshot: RepositorySnapshot) -> DiffArtifact:
        """Load and parse one bounded diff between resolved commits."""
        client = GitClient(snapshot.repository_root, self._settings)
        patch = client.diff(snapshot.base_commit, snapshot.candidate_commit)
        if len(patch.encode("utf-8")) > self._settings.max_diff_bytes:
            raise RepositoryIntakeError("diff_byte_limit")
        changed_paths, additions, deletions = _parse_patch(patch)
        if len(changed_paths) > self._settings.max_changed_files:
            raise RepositoryIntakeError("changed_file_limit")
        return DiffArtifact(
            patch=patch,
            changed_paths=changed_paths,
            summary=DiffSummary(
                changed_file_count=len(changed_paths),
                changed_python_file_count=sum(
                    changed_path.path.suffix == ".py" for changed_path in changed_paths
                ),
                additions=additions,
                deletions=deletions,
            ),
        )

    def preview(self, request: RepositoryRefRequest) -> AnalysisPreview:
        """Resolve and summarize a patch without persisting an analysis run."""
        snapshot = self._resolve_refs(request)
        diff = self.load_diff(snapshot)
        return AnalysisPreview(
            repository_root=snapshot.repository_root,
            base_commit=snapshot.base_commit,
            candidate_commit=snapshot.candidate_commit,
            repository_id=snapshot.repository_id,
            changed_paths=diff.changed_paths,
            summary=diff.summary,
            diagnostics=diff.diagnostics,
        )

    def _resolve_refs(self, request: RepositoryRefRequest) -> RepositorySnapshot:
        """Share canonical path and ref resolution between preview and analysis."""
        try:
            repository_root = request.repo_path.resolve(strict=True)
        except OSError as error:
            raise RepositoryIntakeError("invalid_repository_path") from error
        if not repository_root.is_dir():
            raise RepositoryIntakeError("invalid_repository_path")
        git_marker = repository_root / ".git"
        if not git_marker.exists() or git_marker.is_symlink():
            raise RepositoryIntakeError("invalid_repository")

        client = GitClient(repository_root, self._settings)
        base_commit = client.resolve_commit(request.base_ref)
        candidate_commit = client.resolve_commit(request.candidate_ref)
        repository_id = sha256(str(repository_root).encode("utf-8")).hexdigest()
        return RepositorySnapshot(
            repository_root=repository_root,
            base_commit=base_commit,
            candidate_commit=candidate_commit,
            repository_id=repository_id,
        )


def _parse_patch(patch: str) -> tuple[tuple[ChangedPath, ...], int, int]:
    """Parse safe paths, change types, and line counts from a unified Git patch."""
    if not patch:
        return (), 0, 0
    sections = _split_diff_sections(patch)
    changed_paths: list[ChangedPath] = []
    additions = 0
    deletions = 0
    seen_paths: set[PurePosixPath] = set()
    for section in sections:
        changed_path = _parse_changed_path(section)
        if changed_path.path in seen_paths:
            raise RepositoryIntakeError("duplicate_diff_path")
        seen_paths.add(changed_path.path)
        changed_paths.append(changed_path)
        section_additions, section_deletions = _count_changed_lines(section)
        additions += section_additions
        deletions += section_deletions
    return tuple(changed_paths), additions, deletions


def _split_diff_sections(patch: str) -> tuple[tuple[str, ...], ...]:
    """Split a patch at validated Git file-section headers."""
    sections: list[list[str]] = []
    for line in patch.splitlines():
        if line.startswith(DIFF_SECTION_PREFIX):
            sections.append([line])
        elif sections:
            sections[-1].append(line)
        elif line.strip():
            raise RepositoryIntakeError("invalid_git_diff")
    if not sections:
        raise RepositoryIntakeError("invalid_git_diff")
    return tuple(tuple(section) for section in sections)


def _parse_changed_path(section: tuple[str, ...]) -> ChangedPath:
    """Build one validated changed-path record from a Git diff section."""
    old_header = next((line for line in section if line.startswith(OLD_PATH_PREFIX)), None)
    new_header = next((line for line in section if line.startswith(NEW_PATH_PREFIX)), None)
    if old_header is None or new_header is None:
        raise RepositoryIntakeError("unsupported_git_diff")
    raw_old_path = old_header.removeprefix(OLD_PATH_PREFIX)
    raw_new_path = new_header.removeprefix(NEW_PATH_PREFIX)

    if raw_old_path == NULL_DIFF_PATH:
        path = _parse_prefixed_path(raw_new_path, GIT_NEW_PATH_PREFIX)
        return ChangedPath(path=path, change_type="A")
    if raw_new_path == NULL_DIFF_PATH:
        path = _parse_prefixed_path(raw_old_path, GIT_OLD_PATH_PREFIX)
        return ChangedPath(path=path, change_type="D")

    old_path = _parse_prefixed_path(raw_old_path, GIT_OLD_PATH_PREFIX)
    new_path = _parse_prefixed_path(raw_new_path, GIT_NEW_PATH_PREFIX)
    if old_path != new_path:
        return ChangedPath(path=new_path, old_path=old_path, change_type="R")
    return ChangedPath(path=new_path, change_type="M")


def _parse_prefixed_path(raw_path: str, prefix: str) -> PurePosixPath:
    """Reject quoted or noncanonical diff paths before schema construction."""
    if raw_path.startswith('"') or not raw_path.startswith(prefix):
        raise RepositoryIntakeError("unsupported_git_path")
    relative_path = raw_path.removeprefix(prefix)
    try:
        return ChangedPath.model_validate(
            {"path": relative_path, "change_type": "M"}
        ).path
    except ValueError as error:
        raise RepositoryIntakeError("invalid_git_path") from error


def _count_changed_lines(section: tuple[str, ...]) -> tuple[int, int]:
    """Count added and deleted content lines inside unified-diff hunks."""
    additions = 0
    deletions = 0
    in_hunk = False
    for line in section:
        if line.startswith(HUNK_PREFIX):
            in_hunk = True
        elif in_hunk and line.startswith("+"):
            additions += 1
        elif in_hunk and line.startswith("-"):
            deletions += 1
    return additions, deletions
