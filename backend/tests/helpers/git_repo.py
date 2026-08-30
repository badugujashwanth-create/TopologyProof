"""Git command helpers for trusted fixture tests."""

import subprocess
from pathlib import Path


def run_git(repository: Path, *arguments: str) -> str:
    """Run Git against a trusted test repository and return stdout."""
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    return completed.stdout.strip()
