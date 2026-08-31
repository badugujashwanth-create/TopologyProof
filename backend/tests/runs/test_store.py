"""Run store tests."""
from pathlib import Path

import pytest

from backend.app.errors import TopologyProofError
from backend.app.runs.store import RunStore


def test_store_publication_and_traversal(tmp_path: Path) -> None:
    """Publish UTF-8 artifacts and reject traversal."""
    store=RunStore(tmp_path); store.create("RUN-1", {"ticket":"é"}); store.publish_findings("RUN-1", [{"x":1}]); store.publish_report("RUN-1", "REVIEW REQUIRED — NOT EXECUTED")
    assert "é" in store.read("RUN-1","request.json") and "REVIEW REQUIRED" in store.read("RUN-1","report.md")
    with pytest.raises(TopologyProofError, match="invalid_run_id"): store.create("../outside", {})

def test_interrupted_run(tmp_path: Path) -> None:
    """Mark queued run interrupted without fake completion."""
    store=RunStore(tmp_path); store.create("RUN-2", {}); store.mark_interrupted("RUN-2"); text=store.read("RUN-2","run.json"); assert "restart_interruption" in text and "failed" in text
