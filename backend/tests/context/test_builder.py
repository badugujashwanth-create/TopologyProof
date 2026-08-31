"""Behavior tests for provenance-bounded Python context selection."""

from pathlib import Path, PurePosixPath

import pytest

from backend.app.config import Settings
from backend.app.context.builder import ContextBuilder
from backend.app.ingestion.service import RepositoryIntake
from backend.app.ingestion.symbols import ChangedSymbolDetector
from backend.app.schemas import (
    AnalysisRequest,
    ChangedPath,
    ChangedSymbol,
    DiffArtifact,
    DiffSummary,
    RepositorySnapshot,
)
from backend.tests.helpers.git_repo import run_git
from demo.webhook_dedup.materialize import MaterializedFixture, materialize_fixture


@pytest.fixture
def fixture(tmp_path: Path) -> MaterializedFixture:
    """Materialize the trusted webhook repository used by context tests."""
    return materialize_fixture(tmp_path / "fixture")


def _analysis_inputs(
    fixture: MaterializedFixture,
) -> tuple[AnalysisRequest, RepositorySnapshot, DiffArtifact, tuple[ChangedSymbol, ...]]:
    """Resolve genuine intake artifacts rather than manufacturing context inputs."""
    intake = RepositoryIntake(Settings())
    request = fixture.analysis_request()
    snapshot = intake.resolve(request)
    diff = intake.load_diff(snapshot)
    symbols = ChangedSymbolDetector(Settings()).detect(snapshot, diff)
    return request, snapshot, diff, symbols


def _repository_state(repository: Path) -> tuple[str, str, str, str, str]:
    """Capture all target repository state Task 7 must leave unchanged."""
    return (
        run_git(repository, "status", "--porcelain", "--untracked-files=all"),
        run_git(repository, "rev-parse", "HEAD"),
        run_git(repository, "ls-files", "--stage"),
        run_git(repository, "show-ref"),
        run_git(repository, "config", "--local", "--list"),
    )


def test_context_reaches_route_state_and_one_hop_side_effect(
    fixture: MaterializedFixture,
) -> None:
    """Select changed state, route code, and its one-hop durable side-effect callee."""
    request, snapshot, diff, symbols = _analysis_inputs(fixture)

    items = ContextBuilder(Settings()).build(request, snapshot, diff, symbols)

    assert items[0].symbol == "processed_events"
    assert any(item.path == PurePosixPath("app/main.py") for item in items)
    assert any("event.event_id in processed_events" in item.excerpt for item in items)
    assert any("processed_events.add" in item.excerpt for item in items)
    assert any(item.symbol == "record_payment" for item in items)
    assert all(item.commit == fixture.candidate_ref for item in items)


def test_context_items_preserve_candidate_blob_provenance(
    fixture: MaterializedFixture,
) -> None:
    """Emit source locations that resolve against the requested candidate commit."""
    request, snapshot, diff, symbols = _analysis_inputs(fixture)

    items = ContextBuilder(Settings()).build(request, snapshot, diff, symbols)

    assert all(item.provenance == "candidate_git_blob" for item in items)
    assert all(item.path.as_posix() in {"app/main.py", "app/payments.py"} for item in items)
    assert all(item.line <= item.line_end for item in items)


def test_context_honors_file_budget_deterministically(fixture: MaterializedFixture) -> None:
    """Retain changed-symbol context first when configured file capacity is one."""
    request, snapshot, diff, symbols = _analysis_inputs(fixture)

    items = ContextBuilder(Settings(max_context_files=1)).build(request, snapshot, diff, symbols)

    assert {item.path for item in items} == {PurePosixPath("app/main.py")}
    assert items[0].symbol == "processed_events"


def test_context_excludes_secret_prone_candidate_path(fixture: MaterializedFixture) -> None:
    """Exclude a changed secret-named path before context can reach any provider."""
    request, snapshot, diff, symbols = _analysis_inputs(fixture)
    secret_path = PurePosixPath(".env")
    modified_diff = diff.model_copy(
        update={
            "changed_paths": diff.changed_paths
            + (
                diff.changed_paths[0].model_copy(update={"path": secret_path}),
            ),
            "summary": diff.summary.model_copy(update={"changed_file_count": 3}),
        }
    )

    items = ContextBuilder(Settings()).build(request, snapshot, modified_diff, symbols)

    assert all(item.path != secret_path for item in items)


def test_context_does_not_mutate_target_repository(fixture: MaterializedFixture) -> None:
    """Read only immutable candidate Git blobs while selecting source context."""
    request, snapshot, diff, symbols = _analysis_inputs(fixture)
    before = _repository_state(fixture.repo_path)

    ContextBuilder(Settings()).build(request, snapshot, diff, symbols)

    assert _repository_state(fixture.repo_path) == before


@pytest.mark.parametrize(
    ("path", "content", "commit_message"),
    [
        ("app/binary.py", b"\x00not-python", "add binary candidate blob"),
        ("app/broken.py", b"def broken(:\n", "add malformed candidate source"),
    ],
)
def test_context_excludes_unusable_candidate_python_blobs(
    fixture: MaterializedFixture,
    path: str,
    content: bytes,
    commit_message: str,
) -> None:
    """Skip binary and malformed candidate Python before they can become context."""
    candidate_path = fixture.repo_path / path
    candidate_path.write_bytes(content)
    run_git(fixture.repo_path, "add", path)
    run_git(fixture.repo_path, "commit", "-m", commit_message)
    candidate_ref = run_git(fixture.repo_path, "rev-parse", "HEAD")
    request = fixture.analysis_request().model_copy(
        update={"base_ref": fixture.candidate_ref, "candidate_ref": candidate_ref}
    )
    snapshot = RepositorySnapshot(
        repository_root=fixture.repo_path,
        base_commit=fixture.candidate_ref,
        candidate_commit=candidate_ref,
        repository_id="task7-test-fixture",
    )
    diff = DiffArtifact(
        patch="",
        changed_paths=(ChangedPath(path=PurePosixPath(path), change_type="A"),),
        summary=DiffSummary(
            changed_file_count=1,
            changed_python_file_count=1,
            additions=1,
            deletions=0,
        ),
    )

    items = ContextBuilder(Settings()).build(request, snapshot, diff, ())

    assert items == ()
