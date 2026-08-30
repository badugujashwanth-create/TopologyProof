"""Security and read-only behavior tests for the bounded Git client."""

from io import BytesIO
from pathlib import Path, PurePosixPath
from threading import Event
from typing import Self

import pytest

from backend.app.config import Settings
from backend.app.errors import TopologyProofError
from backend.app.ingestion.git_client import GitClient
from backend.tests.helpers.git_repo import run_git
from demo.webhook_dedup.materialize import MaterializedFixture, materialize_fixture


@pytest.fixture
def fixture(tmp_path: Path) -> MaterializedFixture:
    """Materialize the trusted repository used for bounded Git reads."""
    return materialize_fixture(tmp_path / "fixture")


@pytest.fixture
def client(fixture: MaterializedFixture) -> GitClient:
    """Create a Git client rooted at the trusted fixture repository."""
    return GitClient(fixture.repo_path, Settings())


def snapshot_worktree(repository: Path) -> tuple[str, str, str]:
    """Capture observable repository state before a read-only client operation."""
    return (
        run_git(repository, "status", "--porcelain"),
        run_git(repository, "rev-parse", "HEAD"),
        run_git(repository, "diff", "--binary", "HEAD"),
    )


def test_resolve_commit_returns_the_full_fixture_commit(
    client: GitClient, fixture: MaterializedFixture
) -> None:
    """Catch reference resolution that does not return a canonical commit identifier."""
    assert client.resolve_commit("HEAD") == fixture.candidate_ref


def test_option_like_ref_is_rejected(client: GitClient) -> None:
    """Catch validation that lets a ref alter the fixed Git command shape."""
    with pytest.raises(TopologyProofError, match="invalid_git_ref"):
        client.resolve_commit("--upload-pack=evil")


@pytest.mark.parametrize("ref", ["", " ", "main\x00evil"])
def test_blank_or_nul_ref_is_rejected(client: GitClient, ref: str) -> None:
    """Catch unsafe references before they are passed to Git."""
    with pytest.raises(TopologyProofError, match="invalid_git_ref"):
        client.resolve_commit(ref)


@pytest.mark.parametrize("ref", ["HEAD~1", "HEAD@{1}"])
def test_revision_expression_is_rejected(client: GitClient, ref: str) -> None:
    """Catch ref validation that accepts revision expressions outside the named-ref boundary."""
    with pytest.raises(TopologyProofError, match="invalid_git_ref"):
        client.resolve_commit(ref)


def test_missing_root_is_mapped_to_a_typed_error(tmp_path: Path) -> None:
    """Catch constructor failures that leak filesystem exceptions from untrusted roots."""
    with pytest.raises(TopologyProofError, match="invalid_git_root"):
        GitClient(tmp_path / "missing", Settings())


def test_blob_read_does_not_mutate_target(client: GitClient, fixture: MaterializedFixture) -> None:
    """Catch blob reads that change the checked-out fixture repository."""
    before = snapshot_worktree(fixture.repo_path)

    blob = client.read_blob(fixture.candidate_ref, PurePosixPath("app/main.py"))

    assert "processed_events" in blob
    assert snapshot_worktree(fixture.repo_path) == before


@pytest.mark.parametrize("path", [PurePosixPath("/etc/passwd"), PurePosixPath("app/../main.py")])
def test_absolute_or_parent_path_is_rejected(client: GitClient, path: PurePosixPath) -> None:
    """Catch paths that could escape the repository-relative blob boundary."""
    with pytest.raises(TopologyProofError, match="invalid_git_path"):
        client.read_blob("a" * 40, path)


def test_tree_listing_returns_only_repository_relative_files(
    client: GitClient, fixture: MaterializedFixture
) -> None:
    """Catch tree parsing that loses the fixture's tracked file paths."""
    entries = client.list_tree(fixture.candidate_ref)

    assert tuple(entry.path.as_posix() for entry in entries) == (
        "app/main.py",
        "app/payments.py",
    )
    assert {entry.object_type for entry in entries} == {"blob"}


def test_diff_returns_the_fixture_change_without_mutating_target(
    client: GitClient, fixture: MaterializedFixture
) -> None:
    """Catch a diff command that omits the candidate change or alters the fixture."""
    before = snapshot_worktree(fixture.repo_path)

    patch = client.diff(fixture.base_ref, fixture.candidate_ref)

    assert "processed_events" in patch
    assert snapshot_worktree(fixture.repo_path) == before


def test_blob_read_rejects_output_larger_than_the_configured_limit(
    fixture: MaterializedFixture,
) -> None:
    """Catch source reads that retain more bytes than the configured source limit."""
    client = GitClient(
        fixture.repo_path,
        Settings(max_source_file_bytes=1),
    )

    with pytest.raises(TopologyProofError, match="git_output_limit"):
        client.read_blob(fixture.candidate_ref, PurePosixPath("app/main.py"))


class StreamingGitProcess:
    """Simulate a Git process whose stdout exceeds the client limit in one chunk."""

    def __init__(self, stdout: bytes) -> None:
        """Provide bounded pipe-like streams and record termination."""
        self.stdout = BytesIO(stdout)
        self.stderr = BytesIO()
        self.returncode: int | None = None
        self.was_terminated = False

    def poll(self) -> int | None:
        """Report the process state used by the bounded collector."""
        return self.returncode

    def __enter__(self) -> Self:
        """Support the legacy subprocess.run context-manager protocol during RED."""
        return self

    def __exit__(self, *arguments: object) -> None:
        """Support the legacy subprocess.run context-manager protocol during RED."""
        del arguments

    def communicate(self, input: object = None, timeout: float | None = None) -> tuple[bytes, bytes]:
        """Expose the whole stream only to prove the old collector is not bounded."""
        del input, timeout
        self.returncode = 0
        return self.stdout.read(), self.stderr.read()

    def terminate(self) -> None:
        """Record the termination required once output crosses the configured bound."""
        self.was_terminated = True
        self.returncode = 1

    def wait(self, timeout: float | None = None) -> int:
        """Finish the simulated process without blocking the collector."""
        del timeout
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def test_streaming_limit_terminates_the_process_before_retaining_full_output(
    fixture: MaterializedFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch collectors that wait for an oversized Git stream before enforcing its limit."""
    process = StreamingGitProcess(b"x" * 2)
    client = GitClient(fixture.repo_path, Settings(max_source_file_bytes=1))
    monkeypatch.setattr(
        "backend.app.ingestion.git_client.subprocess.Popen",
        lambda *args, **kwargs: process,
    )

    with pytest.raises(TopologyProofError, match="git_output_limit"):
        client.read_blob(fixture.candidate_ref, PurePosixPath("app/main.py"))

    assert process.was_terminated


class BlockingGitStream:
    """Simulate a pipe that unblocks only after the collector closes it."""

    def __init__(self) -> None:
        """Start the stream in its blocking state."""
        self.closed_event = Event()
        self.reader_finished = Event()

    def read(self, size: int) -> bytes:
        """Block until close, modeling a child that has stopped producing output."""
        del size
        self.closed_event.wait()
        self.reader_finished.set()
        return b""

    def close(self) -> None:
        """Unblock the associated reader thread."""
        self.closed_event.set()


class TimeoutGitProcess:
    """Simulate a process that times out while both captured streams block."""

    def __init__(self) -> None:
        """Provide two blocking pipes and a terminable process state."""
        self.stdout = BlockingGitStream()
        self.stderr = BlockingGitStream()
        self.returncode: int | None = None

    def poll(self) -> int | None:
        """Report the process state used by the bounded collector."""
        return self.returncode

    def terminate(self) -> None:
        """Finish the simulated child without closing its inherited pipe handles."""
        self.returncode = 1

    def wait(self, timeout: float | None = None) -> int:
        """Return promptly after simulated process termination."""
        del timeout
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def test_timeout_closes_blocked_streams_before_returning_a_typed_error(
    fixture: MaterializedFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch timeout paths that abandon blocked output-reader threads."""
    process = TimeoutGitProcess()
    client = GitClient(fixture.repo_path, Settings(git_command_timeout_seconds=1))
    monkeypatch.setattr(
        "backend.app.ingestion.git_client.subprocess.Popen",
        lambda *args, **kwargs: process,
    )

    try:
        with pytest.raises(TopologyProofError, match="git_timeout"):
            client.read_blob(fixture.candidate_ref, PurePosixPath("app/main.py"))
        assert process.stdout.closed_event.is_set()
        assert process.stderr.closed_event.is_set()
        assert process.stdout.reader_finished.is_set()
        assert process.stderr.reader_finished.is_set()
    finally:
        process.stdout.close()
        process.stderr.close()
