"""API dependency composition."""
from backend.app.config import get_settings
from backend.app.runs.executor import InProcessExecutor
from backend.app.runs.orchestrator import AnalysisOrchestrator
from backend.app.runs.store import RunStore


def get_executor() -> InProcessExecutor:
    """Compose the offline executor."""
    store=RunStore(get_settings().artifact_root); return InProcessExecutor(AnalysisOrchestrator(get_settings(),store))
