"""Compare Phase 29 and repaired default-off engines in isolated processes."""

import hashlib
import json
import subprocess
import sys

BASE = "/home/cxiong/codex-runs/codex1-phase35-implementation/baseline-repo/cipp-learning-AbhiCIPP"
REPAIR = "/home/cxiong/codex-runs/codex1-phase35-conformance-repair/repo/cipp-learning-AbhiCIPP"

PROGRAM = r'''import hashlib,json,sys
sys.path.insert(0,sys.argv[1])
from backend.simulation import SimulationEngine
e=SimulationEngine(seed=7)
rows=[]
for _ in range(100):
 e.step()
 rows.append({'t':e.timestep,'spiked':sorted((k,bool(v)) for k,v in e.spiked.items()),'weights':e._all_weights()})
print(hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest())'''


def snapshot(path):
    return subprocess.check_output([sys.executable, "-c", PROGRAM, path], text=True).strip()


if __name__ == "__main__":
    base, repair = snapshot(BASE), snapshot(REPAIR)
    result = {"base": base, "repair": repair, "match": base == repair, "steps": 100}
    print(json.dumps(result, indent=2, sort_keys=True))
    assert result["match"]
