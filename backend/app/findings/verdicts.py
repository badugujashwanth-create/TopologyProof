"""Verdict policy."""
from backend.app.schemas.common import FindingVerdict, OverallVerdict
from backend.app.schemas.findings import Finding


class VerdictPolicy:
    """Apply locked M1 verdict semantics."""
    def finding_verdict(self, finding: Finding) -> FindingVerdict:
        """Return the finding-level verdict."""
        return finding.verdict
    def overall(self, findings: tuple[Finding, ...] | list[Finding], runtime: object = None) -> OverallVerdict:
        """Never return static RED; require future runtime confirmation."""
        del runtime
        if any(item.verdict is FindingVerdict.HIGH_RISK for item in findings):
            return OverallVerdict.REVIEW_REQUIRED
        return OverallVerdict.NO_TESTED_TOPOLOGY_FAILURE
