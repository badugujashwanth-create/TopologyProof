"""Changed-symbol tests for candidate Git blobs and unified-diff hunks."""

from pathlib import Path

import pytest

from backend.app.config import Settings
from backend.app.ingestion.service import RepositoryIntake
from backend.app.ingestion.symbols import ChangedSymbolDetector
from backend.tests.helpers.git_repo import run_git
from demo.webhook_dedup.materialize import MaterializedFixture, materialize_fixture


@pytest.fixture
def fixture(tmp_path: Path) -> MaterializedFixture:
    """Materialize the real webhook fixture for symbol detection."""
    return materialize_fixture(tmp_path / "fixture")


def test_fixture_detects_changed_definitions_and_assignment_targets(
    fixture: MaterializedFixture,
) -> None:
    """Map genuine candidate hunks to Python definitions and assignment targets."""
    intake = RepositoryIntake(Settings())
    snapshot = intake.resolve(fixture.analysis_request())
    diff = intake.load_diff(snapshot)
    detector = ChangedSymbolDetector(Settings())

    symbols = detector.detect(snapshot, diff)

    assert any(
        symbol.name == "processed_events"
        and symbol.kind == "variable"
        and symbol.path.as_posix() == "app/main.py"
        and symbol.new_line_start == 8
        and symbol.new_line_end == 8
        and symbol.candidate_commit == fixture.candidate_ref
        for symbol in symbols
    )
    assert any(
        symbol.name == "receive_payment_webhook" and symbol.kind == "function"
        for symbol in symbols
    )
    assert detector.diagnostics == ()


def test_detector_uses_validated_default_settings(fixture: MaterializedFixture) -> None:
    """Preserve the plan-defined no-argument detector construction path."""
    intake = RepositoryIntake(Settings())
    snapshot = intake.resolve(fixture.analysis_request())
    diff = intake.load_diff(snapshot)

    symbols = ChangedSymbolDetector().detect(snapshot, diff)

    assert any(symbol.name == "processed_events" for symbol in symbols)


def test_detector_reads_candidate_blob_instead_of_dirty_worktree(
    fixture: MaterializedFixture,
) -> None:
    """Keep symbol detection tied to the resolved candidate object, not checkout text."""
    intake = RepositoryIntake(Settings())
    snapshot = intake.resolve(fixture.analysis_request())
    diff = intake.load_diff(snapshot)
    checked_out_source = fixture.repo_path / "app" / "main.py"
    checked_out_source.write_text("not valid python !!!", encoding="utf-8")

    symbols = ChangedSymbolDetector(Settings()).detect(snapshot, diff)

    assert any(symbol.name == "processed_events" for symbol in symbols)


def test_syntax_error_becomes_nonfatal_diagnostic(tmp_path: Path) -> None:
    """Record invalid candidate Python as a diagnostic instead of crashing analysis."""
    fixture = materialize_fixture(tmp_path / "fixture")
    invalid_path = fixture.repo_path / "app" / "broken.py"
    invalid_path.write_text("def broken(:\n", encoding="utf-8")
    run_git(fixture.repo_path, "add", "app/broken.py")
    run_git(fixture.repo_path, "commit", "-m", "add malformed python")
    candidate_commit = run_git(fixture.repo_path, "rev-parse", "HEAD")
    request = fixture.analysis_request().model_copy(update={"candidate_ref": candidate_commit})
    intake = RepositoryIntake(Settings())
    snapshot = intake.resolve(request)
    diff = intake.load_diff(snapshot)
    detector = ChangedSymbolDetector(Settings())

    symbols = detector.detect(snapshot, diff)

    assert all(symbol.path.as_posix() != "app/broken.py" for symbol in symbols)
    assert detector.diagnostics == ("python_syntax_error:app/broken.py:1",)


def test_deleted_python_file_is_not_read_from_candidate(tmp_path: Path) -> None:
    """Skip candidate-blob reads for Python files deleted by the patch."""
    fixture = materialize_fixture(tmp_path / "fixture")
    deleted_path = fixture.repo_path / "app" / "payments.py"
    deleted_path.unlink()
    run_git(fixture.repo_path, "add", "app/payments.py")
    run_git(fixture.repo_path, "commit", "-m", "remove payment module")
    candidate_commit = run_git(fixture.repo_path, "rev-parse", "HEAD")
    request = fixture.analysis_request().model_copy(
        update={"base_ref": fixture.candidate_ref, "candidate_ref": candidate_commit}
    )
    intake = RepositoryIntake(Settings())
    snapshot = intake.resolve(request)
    diff = intake.load_diff(snapshot)
    detector = ChangedSymbolDetector(Settings())

    symbols = detector.detect(snapshot, diff)

    assert symbols == ()
    assert detector.diagnostics == ()
