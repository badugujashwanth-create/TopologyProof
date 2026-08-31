import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class BaselineResult: case_id:str; predicted_risk:bool; evidence:tuple[str,...]; rationale:str
class DiffOnlyBaseline:
 def evaluate(self,repository,base_ref,candidate_ref,ticket):
  diff=subprocess.check_output(['git','-C',str(repository),'diff',base_ref,candidate_ref,'--','*.py'],text=True)
  mutable=bool(re.search(r'\b(set|dict|list)\s*\(',diff)); guard=bool(re.search(r'\bin\s+\w+',diff)); durable=bool(re.search(r'\b(save|insert|create|record|persist|charge|payment|write|commit)\w*\s*\(',diff,re.IGNORECASE)); risk=mutable and guard and durable
  return BaselineResult(repository.name,risk,tuple(x.strip() for x in diff.splitlines() if x.strip())[:3],"diff-only structural heuristic")
