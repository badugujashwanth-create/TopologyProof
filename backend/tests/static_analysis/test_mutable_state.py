"""Behavior tests for module-level mutable-state detection."""

from pathlib import Path, PurePosixPath

import pytest

from backend.app.config import Settings
from backend.app.context.builder import ContextBuilder
from backend.app.schemas import (
    ChangedPath,
    ContextItem,
    DiffArtifact,
    DiffSummary,
    RepositorySnapshot,
)
from backend.app.static_analysis.mutable_state import MutableStateScanner
from demo.webhook_dedup.materialize import MaterializedFixture, materialize_fixture


@pytest.fixture
def fixture(tmp_path: Path) -> MaterializedFixture:
    """Materialize the trusted webhook repository used by signal tests."""
    return materialize_fixture(tmp_path / "fixture")


def _webhook_inputs(
    fixture: MaterializedFixture,
) -> tuple[RepositorySnapshot, DiffArtifact, tuple[ContextItem, ...]]:
    """Build Task 7 inputs using the fixture's typed candidate references."""
    request, snapshot, diff, symbols = fixture.context_inputs()
    context = ContextBuilder(Settings()).build(request, snapshot, diff, symbols)
    return snapshot, diff, context


def test_module_level_set_signal_records_membership_and_mutation(
    fixture: MaterializedFixture,
) -> None:
    """Record factual process-local state relationships without a product verdict."""
    snapshot, diff, context = _webhook_inputs(fixture)
    signals = MutableStateScanner(Settings()).scan(snapshot, diff, context)
    signal = next(signal for signal in signals if signal.symbol == "processed_events")
    assert signal.kind == "module_mutable_collection"
    assert signal.facts["collection_kind"] == "set"
    assert signal.facts["module_local"] is True
    assert signal.facts["membership_tested"] is True
    assert signal.facts["mutation_observed"] is True
    assert signal.facts["correctness_link"] is True
    assert not hasattr(signal, "severity")
    assert not hasattr(signal, "verdict")


@pytest.mark.parametrize(
    ("source", "expected_kind"),
    [
        ("state = {}\n", "dict"),
        ("state = []\n", "list"),
        ("state = set()\n", "set"),
        ("state = {item for item in values}\n", "set"),
        ("state = {key: value for key, value in pairs}\n", "dict"),
        ("state = [item for item in values]\n", "list"),
    ],
)
def test_scanner_detects_supported_module_mutable_forms(
    source: str, expected_kind: str
) -> None:
    """Recognize literal, constructor, and comprehension forms deterministically."""
    snapshot = RepositorySnapshot(
        repository_root=Path("D:/fixture").resolve(),
        base_commit="a" * 40,
        candidate_commit="b" * 40,
        repository_id="fixture",
    )
    diff = DiffArtifact(
        patch="",
        changed_paths=(ChangedPath(path=PurePosixPath("app/cache.py"), change_type="M"),),
        summary=DiffSummary(changed_file_count=1, changed_python_file_count=1, additions=1, deletions=0),
    )
    context = ContextBuilder.items_from_source(
        path=PurePosixPath("app/cache.py"),
        commit=snapshot.candidate_commit,
        source=source,
        selection_reason="test_fixture",
    )
    signals = MutableStateScanner(Settings()).scan(snapshot, diff, context)
    assert signals[0].facts["collection_kind"] == expected_kind


def test_cache_only_global_remains_signal_without_correctness_link() -> None:
    """Avoid treating a mutable performance cache as a topology correctness finding."""
    snapshot = RepositorySnapshot(
        repository_root=Path("D:/fixture").resolve(),
        base_commit="a" * 40,
        candidate_commit="b" * 40,
        repository_id="fixture",
    )
    diff = DiffArtifact(
        patch="",
        changed_paths=(ChangedPath(path=PurePosixPath("app/cache.py"), change_type="M"),),
        summary=DiffSummary(changed_file_count=1, changed_python_file_count=1, additions=1, deletions=0),
    )
    context = ContextBuilder.items_from_source(
        path=PurePosixPath("app/cache.py"),
        commit=snapshot.candidate_commit,
        source="cache = {}\ndef lookup(key: str) -> str:\n    return cache.get(key, key)\n",
        selection_reason="test_fixture",
    )
    signals = MutableStateScanner(Settings()).scan(snapshot, diff, context)
    assert signals[0].kind == "module_mutable_collection"
    assert signals[0].facts["correctness_link"] is False


def test_scanner_is_reusable_for_multiple_contexts() -> None:
    """Retain scanner configuration across independent deterministic scans."""
    snapshot = RepositorySnapshot(
        repository_root=Path("D:/fixture").resolve(),
        base_commit="a" * 40,
        candidate_commit="b" * 40,
        repository_id="fixture",
    )
    diff = DiffArtifact(
        patch="",
        changed_paths=(ChangedPath(path=PurePosixPath("app/cache.py"), change_type="M"),),
        summary=DiffSummary(changed_file_count=1, changed_python_file_count=1, additions=1, deletions=0),
    )
    context = ContextBuilder.items_from_source(
        path=PurePosixPath("app/cache.py"),
        commit=snapshot.candidate_commit,
        source="cache = {}\n",
        selection_reason="test_fixture",
    )
    scanner = MutableStateScanner(Settings())

    scanner.scan(snapshot, diff, context)
    signals = scanner.scan(snapshot, diff, context)

    assert signals[0].symbol == "cache"
