"""Run a fixed, bounded set of read-only Git commands."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from typing import BinaryIO

from backend.app.config import Settings
from backend.app.errors import TopologyProofError

GIT_EXECUTABLE = "git"
GIT_COMMIT_ID_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")
GIT_NAMED_REF_PATTERN = re.compile(r"^(?:HEAD|[A-Za-z0-9][A-Za-z0-9._/-]*)$")
MAX_RESOLVED_COMMIT_BYTES = 256
MAX_GIT_STDERR_BYTES = 16_384
GIT_STREAM_CHUNK_BYTES = 4_096
GIT_TERMINATION_GRACE_SECONDS = 1
CONTROLLED_GIT_ENVIRONMENT = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "LC_ALL": "C",
    "LANG": "C",
}
WINDOWS_ENVIRONMENT_KEYS = ("COMSPEC", "PATHEXT", "SYSTEMROOT", "WINDIR")


class GitClientError(TopologyProofError):
    """Describe a rejected or unsuccessful bounded Git operation."""


@dataclass(frozen=True, slots=True)
class GitCommandResult:
    """Capture the bounded output of one fixed Git invocation."""

    arguments: tuple[str, ...]
    stdout: str
    stderr: str
    return_code: int


@dataclass(frozen=True, slots=True)
class TreeEntry:
    """Describe one repository-relative entry from a resolved Git tree."""

    mode: str
    object_type: str
    object_id: str
    path: PurePosixPath


class GitClient:
    """Provide bounded, shell-free reads from one canonical Git worktree."""

    def __init__(self, root: Path, settings: Settings) -> None:
        """Bind this client to an existing repository root and validated settings."""
        try:
            canonical_root = root.resolve(strict=True)
        except (OSError, TypeError) as error:
            raise GitClientError("invalid_git_root") from error
        if not canonical_root.is_dir():
            raise GitClientError("invalid_git_root")
        self._root = canonical_root
        self._settings = settings
        self._environment = self._build_controlled_environment()

    def resolve_commit(self, ref: str) -> str:
        """Resolve one validated Git reference to its full lowercase commit ID."""
        self._validate_ref(ref)
        result = self._run(("rev-parse", "--verify", f"{ref}^{{commit}}"), MAX_RESOLVED_COMMIT_BYTES)
        commit_id = result.stdout.strip()
        if not GIT_COMMIT_ID_PATTERN.fullmatch(commit_id):
            raise GitClientError("invalid_git_commit")
        return commit_id

    def read_blob(self, commit_id: str, path: PurePosixPath) -> str:
        """Read one validated text blob from an already resolved commit."""
        self._validate_commit_id(commit_id)
        canonical_path = self._validate_path(path)
        result = self._run(
            ("show", "--no-textconv", f"{commit_id}:{canonical_path.as_posix()}"),
            self._settings.max_source_file_bytes,
            decode_error_code="binary_git_blob",
        )
        if "\x00" in result.stdout:
            raise GitClientError("binary_git_blob")
        return result.stdout

    def list_tree(self, commit_id: str) -> tuple[TreeEntry, ...]:
        """List repository-relative tree entries from an already resolved commit."""
        self._validate_commit_id(commit_id)
        result = self._run(("ls-tree", "-r", "-z", commit_id), self._settings.max_diff_bytes)
        return tuple(self._parse_tree_entry(record) for record in result.stdout.split("\x00") if record)

    def diff(self, base_commit: str, candidate_commit: str) -> str:
        """Return the bounded textual diff between two resolved commits."""
        self._validate_commit_id(base_commit)
        self._validate_commit_id(candidate_commit)
        result = self._run(
            (
                "diff",
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--binary",
                base_commit,
                candidate_commit,
            ),
            self._settings.max_diff_bytes,
        )
        if "\x00" in result.stdout:
            raise GitClientError("binary_git_diff")
        return result.stdout

    @staticmethod
    def _build_controlled_environment() -> dict[str, str]:
        """Create the minimal process environment needed for deterministic Git reads."""
        environment = {
            "PATH": os.environ.get("PATH", ""),
            **CONTROLLED_GIT_ENVIRONMENT,
        }
        for key in WINDOWS_ENVIRONMENT_KEYS:
            value = os.environ.get(key)
            if value is not None:
                environment[key] = value
        return environment

    def _run(
        self,
        arguments: tuple[str, ...],
        output_limit: int,
        *,
        decode_error_code: str = "invalid_git_output",
    ) -> GitCommandResult:
        """Execute one fixed read-only Git command with bounded captured output."""
        command = [GIT_EXECUTABLE, "--no-optional-locks", *arguments]
        try:
            process = subprocess.Popen(
                command,
                cwd=self._root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                env=self._environment,
                text=False,
            )
        except OSError as error:
            raise GitClientError("git_unavailable") from error

        stdout, stderr = self._collect_output(process, output_limit)
        result = GitCommandResult(
            arguments=arguments,
            stdout=self._decode_output(stdout, decode_error_code),
            stderr=self._decode_output(stderr, "invalid_git_output"),
            return_code=process.returncode,
        )
        if result.return_code != 0:
            raise GitClientError("git_command_failed")
        return result

    @staticmethod
    def _decode_output(value: bytes, error_code: str) -> str:
        """Decode bounded Git output only after its byte limit has been enforced."""
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError as error:
            raise GitClientError(error_code) from error

    def _collect_output(
        self, process: subprocess.Popen[bytes], stdout_limit: int
    ) -> tuple[bytes, bytes]:
        """Stream process pipes into bounded buffers and terminate on limit or timeout."""
        if process.stdout is None or process.stderr is None:
            self._terminate_process(process)
            raise GitClientError("invalid_git_output")

        chunks: Queue[tuple[str, bytes | None]] = Queue(maxsize=2)
        readers = (
            Thread(target=self._read_stream, args=("stdout", process.stdout, chunks), daemon=True),
            Thread(target=self._read_stream, args=("stderr", process.stderr, chunks), daemon=True),
        )
        for reader in readers:
            reader.start()

        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []
        stdout_size = 0
        stderr_size = 0
        completed_streams = 0
        output_exceeded = False
        deadline = monotonic() + self._settings.git_command_timeout_seconds

        while completed_streams < len(readers):
            remaining_seconds = deadline - monotonic()
            if remaining_seconds <= 0:
                self._stop_readers(process, readers, chunks)
                raise GitClientError("git_timeout")
            try:
                stream_name, chunk = chunks.get(timeout=remaining_seconds)
            except Empty as error:
                self._stop_readers(process, readers, chunks)
                raise GitClientError("git_timeout") from error
            if chunk is None:
                completed_streams += 1
                continue
            if stream_name == "stdout":
                stdout_size += len(chunk)
                if stdout_size <= stdout_limit:
                    stdout_chunks.append(chunk)
                else:
                    output_exceeded = True
            else:
                stderr_size += len(chunk)
                if stderr_size <= MAX_GIT_STDERR_BYTES:
                    stderr_chunks.append(chunk)
                else:
                    output_exceeded = True
            if output_exceeded:
                self._terminate_process(process)

        if output_exceeded:
            raise GitClientError("git_output_limit")
        try:
            process.wait(timeout=max(0, deadline - monotonic()))
        except subprocess.TimeoutExpired as error:
            self._stop_readers(process, readers, chunks)
            raise GitClientError("git_timeout") from error
        return b"".join(stdout_chunks), b"".join(stderr_chunks)

    def _stop_readers(
        self,
        process: subprocess.Popen[bytes],
        readers: tuple[Thread, ...],
        chunks: Queue[tuple[str, bytes | None]],
    ) -> None:
        """Terminate Git, close pipes, and drain reader queues before reporting a timeout."""
        self._terminate_process(process)
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    continue

        deadline = monotonic() + GIT_TERMINATION_GRACE_SECONDS
        while any(reader.is_alive() for reader in readers):
            remaining_seconds = deadline - monotonic()
            if remaining_seconds <= 0:
                break
            try:
                chunks.get(timeout=remaining_seconds)
            except Empty:
                break
        for reader in readers:
            reader.join(timeout=max(0, deadline - monotonic()))

    @staticmethod
    def _read_stream(
        stream_name: str, stream: BinaryIO, chunks: Queue[tuple[str, bytes | None]]
    ) -> None:
        """Copy one process stream in fixed-size chunks without retaining excess data."""
        while chunk := stream.read(GIT_STREAM_CHUNK_BYTES):
            chunks.put((stream_name, chunk))
        chunks.put((stream_name, None))

    @staticmethod
    def _terminate_process(process: subprocess.Popen[bytes]) -> None:
        """Stop a process before returning a bounded-output or timeout error."""
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=GIT_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=GIT_TERMINATION_GRACE_SECONDS)

    @staticmethod
    def _parse_tree_entry(record: str) -> TreeEntry:
        """Parse one NUL-delimited ls-tree record into a validated tree entry."""
        metadata, separator, raw_path = record.partition("\t")
        fields = metadata.split(" ")
        if not separator or len(fields) != 3:
            raise GitClientError("invalid_git_tree")
        mode, object_type, object_id = fields
        if not GIT_COMMIT_ID_PATTERN.fullmatch(object_id):
            raise GitClientError("invalid_git_tree")
        return TreeEntry(
            mode=mode,
            object_type=object_type,
            object_id=object_id,
            path=GitClient._validate_path(PurePosixPath(raw_path)),
        )

    @staticmethod
    def _validate_ref(ref: str) -> None:
        """Reject references that are blank, malformed, or option-like."""
        if (
            not isinstance(ref, str)
            or not GIT_NAMED_REF_PATTERN.fullmatch(ref)
            or ".." in ref
            or "//" in ref
            or ref.endswith((".", "/"))
            or any(part.startswith(".") or part.endswith(".lock") for part in ref.split("/"))
        ):
            raise GitClientError("invalid_git_ref")

    @staticmethod
    def _validate_commit_id(commit_id: str) -> None:
        """Require callers to use a full commit identifier resolved by this client."""
        if not isinstance(commit_id, str) or not GIT_COMMIT_ID_PATTERN.fullmatch(commit_id):
            raise GitClientError("invalid_git_commit")

    @staticmethod
    def _validate_path(path: PurePosixPath) -> PurePosixPath:
        """Require a canonical repository-relative POSIX path without traversal."""
        if (
            not isinstance(path, PurePosixPath)
            or path.is_absolute()
            or not path.parts
            or path == PurePosixPath(".")
            or ".." in path.parts
            or "\\" in path.as_posix()
            or "\x00" in path.as_posix()
        ):
            raise GitClientError("invalid_git_path")
        return path
