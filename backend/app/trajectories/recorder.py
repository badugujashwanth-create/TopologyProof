"""Trajectory recording."""
import json
from pathlib import Path

from backend.app.schemas.runs import TrajectoryEvent


class TrajectoryRecorder:
    """Persist ordered observable events as JSONL."""
    def __init__(self, path: Path) -> None:
        """Initialize recorder."""; self.path=path; self._events: list[TrajectoryEvent] = []
    def append(self,event: TrajectoryEvent) -> None:
        """Append an event with monotonic step."""
        self._events.append(event); self.path.parent.mkdir(parents=True,exist_ok=True); self.path.write_text("".join(json.dumps(item.model_dump(mode="json"))+"\n" for item in self._events),encoding="utf-8")

