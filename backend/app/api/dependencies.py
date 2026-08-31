"""Application dependency container."""
from dataclasses import dataclass

from backend.app.config import get_settings
from backend.app.runs.executor import InProcessExecutor
from backend.app.runs.orchestrator import AnalysisOrchestrator
from backend.app.runs.store import RunStore


@dataclass
class Container:
    """Compose API services."""
    store: RunStore
    executor: InProcessExecutor
    def create(self, run_id: str, request: object) -> None:
        """Create persisted run."""; self.store.create(run_id,request)
_container=None
def get_container() -> Container:
    """Return singleton service container."""
    global _container
    if _container is None:
        settings=get_settings(); store=RunStore(settings.artifact_root); _container=Container(store,InProcessExecutor(AnalysisOrchestrator(settings,store)))
    return _container
