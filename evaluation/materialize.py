import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Materialized: case_id:str; repo:Path; base_ref:str; candidate_ref:str; ticket:str
def materialize_case(case,destination):
    destination=Path(destination); destination.mkdir(parents=True,exist_ok=False); (destination/'app').mkdir(); (destination/'app/main.py').write_text('def noop():\n    return None\n',encoding='utf8'); subprocess.run(['git','-C',str(destination),'init'],check=True,capture_output=True); subprocess.run(['git','-C',str(destination),'config','user.name','TopologyProof Eval'],check=True); subprocess.run(['git','-C',str(destination),'config','user.email','eval@topologyproof.local'],check=True); subprocess.run(['git','-C',str(destination),'add','.'],check=True); subprocess.run(['git','-C',str(destination),'commit','-m','base'],check=True,capture_output=True); base=subprocess.check_output(['git','-C',str(destination),'rev-parse','HEAD'],text=True).strip(); (destination/'app/main.py').write_text(case['source'],encoding='utf8'); subprocess.run(['git','-C',str(destination),'add','.'],check=True); subprocess.run(['git','-C',str(destination),'commit','-m','candidate'],check=True,capture_output=True); cand=subprocess.check_output(['git','-C',str(destination),'rev-parse','HEAD'],text=True).strip(); return Materialized(case['case_id'],destination.resolve(),base,cand,case['title'])
