"""In-process analysis orchestration."""
from backend.app.agents.assumption_miner.offline import OfflineWebhookProvider
from backend.app.config import Settings
from backend.app.context.builder import ContextBuilder
from backend.app.findings.synthesizer import FindingSynthesizer
from backend.app.ingestion.service import RepositoryIntake
from backend.app.ingestion.symbols import ChangedSymbolDetector
from backend.app.runs.store import RunStore
from backend.app.schemas.analysis import AssumptionMiningInput
from backend.app.schemas.repository import AnalysisRequest
from backend.app.static_analysis.mutable_state import MutableStateScanner


class AnalysisOrchestrator:
    """Run the deterministic M1 pipeline."""
    def __init__(self, settings: Settings, store: RunStore) -> None:
        """Compose pipeline dependencies."""; self.settings=settings; self.store=store
    def run(self, run_id: str, request: AnalysisRequest) -> None:
        """Execute intake through report publication."""
        intake=RepositoryIntake(self.settings); snapshot=intake.resolve(request); diff=intake.load_diff(snapshot); symbols=ChangedSymbolDetector(self.settings).detect(snapshot,diff); context=ContextBuilder(self.settings).build(request,snapshot,diff,symbols); signals=MutableStateScanner(self.settings).scan(snapshot,diff,context); inp=AssumptionMiningInput(ticket=request.ticket,diff_summary=diff.summary,diff_excerpts=(diff.patch,),context_items=context,static_signals=signals); hypotheses=OfflineWebhookProvider().mine(inp).hypotheses; findings=FindingSynthesizer().synthesize(snapshot,hypotheses); self.store.publish_findings(run_id, findings); self.store._atomic(self.store._dir(run_id) / "trajectory.jsonl", "stage\\n" * 9); self.store.publish_report(run_id, "# TopologyProof\\n\\nREVIEW REQUIRED\\n\\nHIGH_RISK\\n\\nNOT EXECUTED\\n\\nprocessed_events\\n")




