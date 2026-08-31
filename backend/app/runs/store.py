"""File-backed run artifact storage."""
import json
import os
from pathlib import Path

from backend.app.errors import TopologyProofError


class RunStore:
    """Persist atomic run artifacts below a configured root."""
    def __init__(self, root: Path) -> None:
        """Initialize artifact root."""; self.root=root.resolve(); self.root.mkdir(parents=True,exist_ok=True)
    def _dir(self, run_id: str) -> Path:
        """Return safe run directory."""
        if not run_id or Path(run_id).name != run_id or ".." in Path(run_id).parts: raise TopologyProofError("invalid_run_id")
        return self.root/run_id
    def create(self, run_id: str, request: object) -> None:
        """Create request and run records."""
        d=self._dir(run_id); d.mkdir(exist_ok=False); self._atomic(d/"request.json", json.dumps(request, default=str)); self._atomic(d/"run.json", json.dumps({"run_id":run_id,"status":"queued"}))
    def read(self, run_id: str, name: str) -> str:
        """Read an artifact."""; return (self._dir(run_id)/name).read_text(encoding="utf-8")
    def publish_findings(self, run_id: str, findings: object) -> None:
        """Publish findings atomically."""; self._atomic(self._dir(run_id)/"findings.json", json.dumps(findings, default=str))
    def publish_report(self, run_id: str, report: str) -> None:
        """Publish Markdown report atomically."""; self._atomic(self._dir(run_id)/"report.md", report)
    def mark_interrupted(self, run_id: str) -> None:
        """Mark an interrupted run failed."""; self._atomic(self._dir(run_id)/"run.json", json.dumps({"run_id":run_id,"status":"failed","error":"restart_interruption"}))
    @staticmethod
    def _atomic(path: Path, content: str) -> None:
        """Write and atomically replace a sibling temporary file."""
        tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(content,encoding="utf-8"); os.replace(tmp,path)
