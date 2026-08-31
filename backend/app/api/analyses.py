"""Analysis API routes."""
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import get_container
from backend.app.schemas.repository import AnalysisRequest

router=APIRouter(prefix="/analyses", tags=["analyses"])

@router.post("", status_code=202)
def create_analysis(request: AnalysisRequest, container=Depends(get_container)) -> dict[str, str]:
    """Create and submit a real offline analysis."""
    run_id=f"RUN-{uuid4().hex[:12]}"; container.create(run_id,request); container.executor.submit(run_id,request); return {"run_id":run_id}

@router.get("/{run_id}")
def get_status(run_id: str, container=Depends(get_container)) -> dict[str, str]:
    """Return run status based on published artifacts."""
    try: container.store.read(run_id,"findings.json"); return {"run_id":run_id,"status":"completed"}
    except FileNotFoundError:
        try: container.store.read(run_id,"run.json"); return {"run_id":run_id,"status":"running"}
        except FileNotFoundError: raise HTTPException(404,"unknown_run")

@router.get("/{run_id}/findings")
def findings(run_id: str, container=Depends(get_container)) -> object:
    """Return published findings."""
    try: return container.store.read(run_id,"findings.json")
    except FileNotFoundError: raise HTTPException(409,"findings_not_ready")

@router.get("/{run_id}/report")
def report(run_id: str, container=Depends(get_container)) -> str:
    """Return published report."""
    try: return str(container.store.read(run_id,"report.md"))
    except FileNotFoundError: raise HTTPException(409,"report_not_ready")


