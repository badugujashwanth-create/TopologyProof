"""Trust-boundary smoke tests."""
from pathlib import Path, PurePosixPath

import pytest

from backend.app.config import Settings
from backend.app.ingestion.git_client import GitClient, GitClientError


def test_traversal_rejected(tmp_path: Path) -> None:
    """Git client rejects hostile paths."""
    client=GitClient(tmp_path,Settings())
    with pytest.raises(GitClientError): client.read_blob("a"*40, PurePosixPath("../outside"))


