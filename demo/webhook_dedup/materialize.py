"""Build a trusted two-commit webhook fixture for local analysis tests."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

from backend.app.schemas import (
    AnalysisRequest,
    ChangedPath,
    ChangedSymbol,
    DiffArtifact,
    DiffSummary,
    RepositorySnapshot,
)

PACKAGE_ROOT = Path(__file__).parent
BASE_SOURCE = PACKAGE_ROOT / "base"
CANDIDATE_SOURCE = PACKAGE_ROOT / "candidate"
TICKET = (PACKAGE_ROOT / "ticket.txt").read_text(encoding="utf-8").strip()
GIT_TIMEOUT_SECONDS = 10
FIXTURE_REPOSITORY_ID = "webhook-dedup-fixture"
CHANGED_MODULE_PATH = "app/main.py"
PROCESSED_EVENTS_LINE = 8


@dataclass(frozen=True, slots=True)
class MaterializedFixture:
    """Describe the clean repository and request inputs created from trusted snapshots."""

    repo_path: Path
    base_ref: str
    candidate_ref: str
    ticket: str

    def analysis_request(self) -> AnalysisRequest:
        """Create the typed analysis request for this trusted repository."""
        return AnalysisRequest(
            repo_path=self.repo_path,
            ticket=self.ticket,
            base_ref=self.base_ref,
            candidate_ref=self.candidate_ref,
        )

    def request_json(self) -> dict[str, object]:
        """Serialize the analysis request for API test callers."""
        return cast(dict[str, object], self.analysis_request().model_dump(mode="json"))

    def context_inputs(
        self,
    ) -> tuple[AnalysisRequest, RepositorySnapshot, DiffArtifact, tuple[ChangedSymbol, ...]]:
        """Provide typed fixture inputs for later bounded context tests."""
        snapshot = RepositorySnapshot(
            repository_root=self.repo_path,
            base_commit=self.base_ref,
            candidate_commit=self.candidate_ref,
            repository_id=FIXTURE_REPOSITORY_ID,
        )
        diff = DiffArtifact(
            patch="",
            changed_paths=(
                ChangedPath(path=PurePosixPath(CHANGED_MODULE_PATH), change_type="M"),
                ChangedPath(path=PurePosixPath("app/payments.py"), change_type="M"),
            ),
            summary=DiffSummary(
                changed_file_count=2,
                changed_python_file_count=2,
                additions=7,
                deletions=3,
            ),
        )
        symbols = (
            ChangedSymbol(
                path=PurePosixPath(CHANGED_MODULE_PATH),
                kind="variable",
                name="processed_events",
                candidate_commit=self.candidate_ref,
                new_line_start=PROCESSED_EVENTS_LINE,
                new_line_end=PROCESSED_EVENTS_LINE,
            ),
        )
        return self.analysis_request(), snapshot, diff, symbols


def _copy_snapshot(source: Path, destination: Path) -> None:
    """Overlay one trusted source snapshot into the new fixture repository."""
    shutil.copytree(source, destination, dirs_exist_ok=True)


def _git(repository: Path, *arguments: str) -> str:
    """Run Git only while constructing the trusted local fixture repository."""
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    return completed.stdout.strip()


def materialize_fixture(destination: Path) -> MaterializedFixture:
    """Create the trusted webhook fixture as a clean two-commit Git repository."""
    destination.mkdir(parents=True, exist_ok=False)
    _copy_snapshot(BASE_SOURCE, destination)
    _git(destination, "init")
    _git(destination, "config", "user.name", "TopologyProof Fixture")
    _git(destination, "config", "user.email", "fixture@topologyproof.local")
    _git(destination, "add", ".")
    _git(destination, "commit", "-m", "base webhook behavior")
    base_commit = _git(destination, "rev-parse", "HEAD")
    _copy_snapshot(CANDIDATE_SOURCE, destination)
    _git(destination, "add", ".")
    _git(destination, "commit", "-m", "prevent duplicate webhook processing")
    candidate_commit = _git(destination, "rev-parse", "HEAD")
    return MaterializedFixture(destination.resolve(), base_commit, candidate_commit, TICKET)


def _parse_arguments() -> argparse.Namespace:
    """Parse the explicit destination required by the fixture CLI."""
    parser = argparse.ArgumentParser(description="Create the trusted webhook Git fixture.")
    parser.add_argument("--destination", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    """Materialize the fixture and print its serializable request fields."""
    arguments = _parse_arguments()
    fixture = materialize_fixture(arguments.destination)
    print(
        json.dumps(
            {
                "repo_path": str(fixture.repo_path),
                "base_ref": fixture.base_ref,
                "candidate_ref": fixture.candidate_ref,
                "ticket": fixture.ticket,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
