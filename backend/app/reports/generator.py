"""Markdown report generation."""
from backend.app.schemas.runs import ReportArtifact
class ReportGenerator:
    """Render deterministic findings reports."""
    def render(self, run: object, findings: object, trajectory: object) -> ReportArtifact:
        """Render a concise report artifact."""
        del trajectory; text=f"# TopologyProof Report\n\nOverall: REVIEW REQUIRED\n\nFindings: {len(findings)}\n"; return ReportArtifact(path="report.md", content=text)
