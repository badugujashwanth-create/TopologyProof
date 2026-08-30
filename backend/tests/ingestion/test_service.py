"""Contract and security tests for repository intake."""

from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.errors import TopologyProofError
from backend.app.ingestion.service import AnalysisPreview, RepositoryIntake
from backend.app.schemas import AnalysisRequest, RepositoryRefRequest
from backend.tests.helpers.git_repo import run_git
from demo.webhook_dedup.materialize import MaterializedFixture, materialize_fixture


@pytest.fixture
def fixture(tmp_path: Path) -> MaterializedFixture:
    """Materialize the trusted two-commit repository used by intake tests."""
    return materialize_fixture(tmp_path / "fixture")


def repository_state(repository: Path) -> tuple[str, str, str, str, str]:
    """Capture worktree, index, ref, and local-config state around analysis."""
    return (
        run_git(repository, "status", "--porcelain", "--untracked-files=all"),
        run_git(repository, "rev-parse", "HEAD"),
        run_git(repository, "ls-files", "--stage"),
        run_git(repository, "show-ref"),
        run_git(repository, "config", "--local", "--list"),
    )


def test_fixture_intake_resolves_refs_and_bounded_diff_without_mutation(
    fixture: MaterializedFixture,
) -> None:
    """Resolve genuine fixture commits and summarize their immutable Git-object diff."""
    intake = RepositoryIntake(Settings())
    before = repository_state(fixture.repo_path)

    snapshot = intake.resolve(fixture.analysis_request())
    diff = intake.load_diff(snapshot)

    assert snapshot.repository_root == fixture.repo_path
    assert snapshot.base_commit == fixture.base_ref
    assert snapshot.candidate_commit == fixture.candidate_ref
    assert len(snapshot.repository_id) == 64
    assert tuple(path.path.as_posix() for path in diff.changed_paths) == (
        "app/main.py",
        "app/payments.py",
    )
    assert tuple(path.change_type for path in diff.changed_paths) == ("M", "M")
    assert diff.summary.changed_file_count == 2
    assert diff.summary.changed_python_file_count == 2
    assert diff.summary.additions == 7
    assert diff.summary.deletions == 3
    assert "processed_events" in diff.patch
    assert repository_state(fixture.repo_path) == before


def test_preview_reuses_resolution_and_diff_contract(fixture: MaterializedFixture) -> None:
    """Return resolved commits and the same changed-path summary without starting analysis."""
    preview = RepositoryIntake(Settings()).preview(
        RepositoryRefRequest(
            repo_path=fixture.repo_path,
            base_ref=fixture.base_ref,
            candidate_ref=fixture.candidate_ref,
        )
    )

    assert isinstance(preview, AnalysisPreview)
    assert preview.base_commit == fixture.base_ref
    assert preview.candidate_commit == fixture.candidate_ref
    assert preview.summary.changed_file_count == 2
    assert tuple(path.path.as_posix() for path in preview.changed_paths) == (
        "app/main.py",
        "app/payments.py",
    )
    assert "patch" not in preview.model_dump(mode="json")


@pytest.mark.parametrize("ref", ["", "--upload-pack=evil", "HEAD~1", "main\x00evil"])
def test_intake_rejects_hostile_refs_without_mutation(
    fixture: MaterializedFixture, ref: str
) -> None:
    """Preserve Task 5 ref validation at the repository-intake boundary."""
    before = repository_state(fixture.repo_path)

    with pytest.raises(TopologyProofError, match="invalid_git_ref"):
        RepositoryIntake(Settings()).resolve(
            fixture.analysis_request().model_copy(update={"base_ref": ref})
        )

    assert repository_state(fixture.repo_path) == before


def test_intake_rejects_existing_non_repository(tmp_path: Path) -> None:
    """Map a directory without a Git worktree marker to a typed intake failure."""
    directory = (tmp_path / "not-a-repository").resolve()
    directory.mkdir()

    with pytest.raises(TopologyProofError, match="invalid_repository"):
        RepositoryIntake(Settings()).resolve(
            fixture_request(directory)
        )


def test_intake_rejects_missing_repository_path(tmp_path: Path) -> None:
    """Map a missing repository path to a typed intake failure."""
    missing = (tmp_path / "missing").resolve()

    with pytest.raises(TopologyProofError, match="invalid_repository_path"):
        RepositoryIntake(Settings()).resolve(fixture_request(missing))


def test_diff_enforces_changed_file_limit(fixture: MaterializedFixture) -> None:
    """Fail closed when a genuine diff exceeds the configured changed-file budget."""
    intake = RepositoryIntake(Settings(max_changed_files=1))
    snapshot = intake.resolve(fixture.analysis_request())

    with pytest.raises(TopologyProofError, match="changed_file_limit"):
        intake.load_diff(snapshot)


def test_diff_enforces_byte_limit(fixture: MaterializedFixture) -> None:
    """Preserve the bounded Git client's byte limit at the intake boundary."""
    intake = RepositoryIntake(Settings(max_diff_bytes=1))
    snapshot = intake.resolve(fixture.analysis_request())

    with pytest.raises(TopologyProofError, match="git_output_limit"):
        intake.load_diff(snapshot)


@pytest.mark.parametrize("path", ["../secret.py", "/absolute.py", "app/../../secret.py"])
def test_diff_rejects_noncanonical_repository_paths(
    fixture: MaterializedFixture, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    """Reject traversal and absolute paths even when they appear in Git diff metadata."""
    intake = RepositoryIntake(Settings())
    snapshot = intake.resolve(fixture.analysis_request())
    hostile_patch = (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -0,0 +1 @@\n"
        "+secret = True\n"
    )

    def return_hostile_diff(*arguments: object) -> str:
        """Return controlled hostile metadata without invoking Git."""
        del arguments
        return hostile_patch

    monkeypatch.setattr(
        "backend.app.ingestion.service.GitClient.diff",
        return_hostile_diff,
    )

    with pytest.raises(TopologyProofError, match="invalid_git_path"):
        intake.load_diff(snapshot)


def fixture_request(repository: Path) -> AnalysisRequest:
    """Build a minimal typed ref request for repository validation tests."""
    return AnalysisRequest(
        repo_path=repository,
        ticket="Prevent duplicate webhook processing.",
        base_ref="a" * 40,
        candidate_ref="b" * 40,
    )
