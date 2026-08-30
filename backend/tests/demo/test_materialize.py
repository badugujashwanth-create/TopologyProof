"""Behavior tests for the reproducible webhook fixture."""

import json
import subprocess
import sys
from pathlib import Path

from backend.app.schemas import AnalysisRequest, DiffArtifact, RepositorySnapshot
from backend.tests.helpers.git_repo import run_git
from demo.webhook_dedup.materialize import materialize_fixture


def test_materializer_creates_clean_two_commit_repository(tmp_path: Path) -> None:
    """Catch a missing commit, dirty target, or absent deduplication change."""
    fixture = materialize_fixture(tmp_path / "fixture")

    assert fixture.repo_path.is_absolute()
    assert run_git(fixture.repo_path, "rev-list", "--count", "HEAD") == "2"
    assert run_git(fixture.repo_path, "status", "--porcelain") == ""
    diff = run_git(fixture.repo_path, "diff", fixture.base_ref, fixture.candidate_ref)
    assert "processed_events" in diff
    assert run_git(
        fixture.repo_path,
        "diff",
        "--numstat",
        fixture.base_ref,
        fixture.candidate_ref,
    ).splitlines() == ["6\t2\tapp/main.py", "1\t1\tapp/payments.py"]
    assert "unsafe" not in fixture.ticket.casefold()


def test_fixture_helpers_expose_typed_inputs_for_later_analysis(tmp_path: Path) -> None:
    """Catch fixture helpers that cannot supply the later analysis boundaries."""
    fixture = materialize_fixture(tmp_path / "fixture")
    request = fixture.analysis_request()
    request_json = fixture.request_json()
    context_request, snapshot, diff, symbols = fixture.context_inputs()

    assert isinstance(request, AnalysisRequest)
    assert request.repo_path == fixture.repo_path
    assert request_json["repo_path"] == str(fixture.repo_path)
    assert context_request == request
    assert isinstance(snapshot, RepositorySnapshot)
    assert snapshot.candidate_commit == fixture.candidate_ref
    assert isinstance(diff, DiffArtifact)
    assert tuple(path.path.as_posix() for path in diff.changed_paths) == (
        "app/main.py",
        "app/payments.py",
    )
    assert diff.summary.changed_file_count == 2
    assert diff.summary.additions == 7
    assert diff.summary.deletions == 3
    assert tuple(symbol.name for symbol in symbols) == ("processed_events",)
    assert symbols[0].new_line_start == 8


def test_materializer_cli_serializes_the_fixture_contract(tmp_path: Path) -> None:
    """Catch a CLI that does not expose the fixture fields to shell workflows."""
    destination = tmp_path / "fixture"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "demo.webhook_dedup.materialize",
            "--destination",
            str(destination),
        ],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert set(payload) == {"repo_path", "base_ref", "candidate_ref", "ticket"}
    assert payload["repo_path"] == str(destination.resolve())
    assert len(payload["base_ref"]) == 40
    assert len(payload["candidate_ref"]) == 40
