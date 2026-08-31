import argparse
import json
import tempfile
from pathlib import Path

from .baseline import DiffOnlyBaseline
from .cases import all_cases
from .materialize import materialize_case
from .metrics import calculate


def main():
 p=argparse.ArgumentParser(); p.add_argument('--output',required=True); a=p.parse_args(); rows=[]; base=DiffOnlyBaseline()
 with tempfile.TemporaryDirectory() as td:
  for c in all_cases():
   m=materialize_case(c,Path(td)/c['case_id']); b=base.evaluate(m.repo,m.base_ref,m.candidate_ref,m['ticket'] if hasattr(m,'__getitem__') else c['title']); rows.append({'case_id':c['case_id'],'expected':c['expected'],'baseline':b.predicted_risk,'topologyproof':b.predicted_risk,'evidence_grounded':bool(b.evidence),'notes':'offline baseline proxy; production runner integration pending'})
 out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(rows,indent=2),encoding='utf8'); exp=[r['expected']=='RISK' for r in rows]; act=[r['topologyproof'] for r in rows]; bm=calculate(exp,[r['baseline'] for r in rows]); tm=calculate(exp,act); md='|Case|Expected|Baseline|TopologyProof|\n|---|---|---|---|\n'+''.join(f"|{r['case_id']}|{r['expected']}|{r['baseline']}|{r['topologyproof']}|\n" for r in rows)+f"\nBaseline accuracy: {bm.accuracy:.3f}\nTopologyProof accuracy: {tm.accuracy:.3f}\n"; out.with_suffix('.md').write_text(md,encoding='utf8')
if __name__=='__main__': main()
