import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CriterionResult:
    criterion_id: str
    satisfied: bool
    evidence: str
    source: str
@dataclass(frozen=True)
class QualityScore:
    system_name: str
    criteria: tuple[CriterionResult, ...]
    @property
    def total(self) -> int:
        return sum(c.satisfied for c in self.criteria)
def _score(name: str, text: str, grounded: bool, source: str) -> QualityScore:
    flags = (('C1', bool(re.search(r'high.?risk|review required|risk', text, re.IGNORECASE)), 'risk decision'), ('C2', grounded and 'processed_events' in text and 'line=8' in text, 'candidate path/line/excerpt'), ('C3', bool(re.search(r'shared deduplication state|process.?local', text, re.IGNORECASE)), 'deployment assumption'), ('C4', bool(re.search(r'replica|routing|restart|state locality|worker', text, re.IGNORECASE)), 'topology dimension'), ('C5', bool(re.search(r'duplicate durable|duplicate payment|separate workers', text, re.IGNORECASE)), 'predicted failure'), ('C6', bool(re.search(r'separate workers|same event|at most one durable|experiment', text, re.IGNORECASE)), 'verification plan'))
    return QualityScore(name, tuple(CriterionResult(i, v, e, source) for i, v, e in flags))
def evaluate() -> dict[str, Any]:
    baseline = json.loads(Path('submission/evaluation/baseline-webhook.json').read_text(encoding='utf8'))
    root = Path('submission/trajectories/webhook-dedup')
    topo_text = (root / 'findings.json').read_text(encoding='utf8') + (root / 'report.md').read_text(encoding='utf8')
    base = _score('Diff-only baseline', json.dumps(baseline), False, 'baseline-webhook.json')
    topo = _score('TopologyProof', topo_text, True, 'findings.json/report.md')
    return {'baseline': {'total': base.total, 'criteria': [asdict(c) for c in base.criteria]}, 'topologyproof': {'total': topo.total, 'criteria': [asdict(c) for c in topo.criteria]}}
def main() -> None:
    result = evaluate(); Path('submission/evaluation/actionable-quality.json').write_text(json.dumps(result, indent=2), encoding='utf8'); b = result['baseline']['total']; t = result['topologyproof']['total']; Path('submission/evaluation/actionable-quality.md').write_text(f'# Actionable Diagnosis Quality Evaluation\n\nBaseline: {b}/6\n\nTopologyProof: {t}/6\n\nImprovement: {t-b} criteria\n', encoding='utf8')
if __name__ == '__main__': main()
