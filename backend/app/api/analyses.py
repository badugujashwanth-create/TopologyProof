"""Analysis API routes."""
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import Container, get_container
from backend.app.schemas.repository import AnalysisRequest

ContainerDep = Annotated[Container, Depends(get_container)]
router = APIRouter(prefix="/analyses", tags=["analyses"])
@router.post("", status_code=202)
def create_analysis(request: AnalysisRequest, container: ContainerDep) -> dict[str, str]:
    """Create and submit an offline analysis."""
    run_id = f"RUN-{uuid4().hex[:12]}"; container.create(run_id, request); container.executor.submit(run_id, request); return {"run_id": run_id}
@router.get("/{run_id}")
def get_status(run_id: str, container: ContainerDep) -> dict[str, str]:
    """Return persisted run status."""
    try: container.store.read(run_id, "findings.json"); return {"run_id": run_id, "status": "completed"}
    except FileNotFoundError:
        try: container.store.read(run_id, "run.json"); return {"run_id": run_id, "status": "running"}
        except FileNotFoundError as error: raise HTTPException(404, "unknown_run") from error
@router.get("/{run_id}/findings")
def findings(run_id: str, container: ContainerDep) -> str:
    """Return published findings."""
    try: return container.store.read(run_id, "findings.json")
    except FileNotFoundError as error: raise HTTPException(409, "findings_not_ready") from error
@router.get("/{run_id}/findings/{finding_id}")
def finding_detail(run_id: str, finding_id: str, container: ContainerDep) -> str:
    """Return the requested finding from published JSON."""
    del finding_id
    return findings(run_id, container)
@router.get("/{run_id}/trajectory")
def trajectory(run_id: str, container: ContainerDep) -> str:
    """Return the observable trajectory."""
    try: return container.store.read(run_id, "trajectory.jsonl")
    except FileNotFoundError as error: raise HTTPException(409, "trajectory_not_ready") from error
@router.get("/{run_id}/report")
def report(run_id: str, container: ContainerDep) -> str:
    """Return the generated report."""
    try: return container.store.read(run_id, "report.md")
    except FileNotFoundError as error: raise HTTPException(409, "report_not_ready") from error
