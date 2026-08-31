"""Trajectory tests."""
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.schemas.common import TrajectoryAction
from backend.app.schemas.runs import TrajectoryEvent
from backend.app.trajectories.recorder import TrajectoryRecorder


def test_recorder_persists_order(tmp_path: Path) -> None:
    """Persist observable events in append order."""
    path=tmp_path/"trajectory.jsonl"; recorder=TrajectoryRecorder(path); stamp=datetime.now(UTC)
    for step in (1,2,3): recorder.append(TrajectoryEvent(run_id="RUN-1",step=step,occurred_at=stamp,component="test",action=TrajectoryAction.REPOSITORY_LOADED,summary=f"event {step}"))
    assert [json.loads(line)["step"] for line in path.read_text(encoding="utf-8").splitlines()] == [1,2,3]
