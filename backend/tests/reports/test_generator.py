"""Report tests."""
from backend.app.reports.generator import ReportGenerator


def test_report_contains_m1_semantics() -> None:
    """Render review-required static result without runtime claims."""
    report=ReportGenerator().render(None,[object()],None).content
    assert "REVIEW REQUIRED" in report
    assert "100% SAFE" not in report
    assert "REPRODUCIBLE TOPOLOGY-SENSITIVE FAILURE" not in report
