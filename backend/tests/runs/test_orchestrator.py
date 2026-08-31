from backend.app.config import Settings
from backend.app.runs.orchestrator import AnalysisOrchestrator
from backend.app.runs.store import RunStore
from demo.webhook_dedup.materialize import materialize_fixture


def test_real_orchestrator_fixture(tmp_path):
    fixture=materialize_fixture(tmp_path/"fixture"); request=fixture.analysis_request(); store=RunStore(tmp_path/"runs"); store.create("RUN-1",request); AnalysisOrchestrator(Settings(),store).run("RUN-1",request); assert "REVIEW REQUIRED" in store.read("RUN-1","report.md"); assert "processed_events" in store.read("RUN-1","report.md")
