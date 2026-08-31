"""In-process execution."""
from concurrent.futures import ThreadPoolExecutor
from typing import Any


class InProcessExecutor:
    """Submit orchestration work to a standard-library executor."""
    def __init__(self, orchestrator: Any) -> None:
        """Store orchestrator."""; self.orchestrator=orchestrator; self.executor=ThreadPoolExecutor(max_workers=1)
    def submit(self, run_id: str, request: object) -> None:
        """Submit one real analysis."""; self.executor.submit(self.orchestrator.run, run_id, request)






