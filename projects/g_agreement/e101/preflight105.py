"""Fresh-extract runtime import, including E105's frozen supplied scorer."""
import json,os,subprocess,sys
from pathlib import Path
from .preflight104 import SCRIPT as BASE
SCRIPT=BASE+'''
from projects.g_agreement.e101 import runner105
from projects.g_agreement.e105 import inputs,scoring
assert callable(runner105.acquire) and callable(scoring.score_batch)
inputs.frozen()
for module in (runner105,inputs,scoring):
    assert Path(module.__file__).resolve().is_relative_to(root)
print(json.dumps(dict(status='PASS',experiment='E105',frozen_scorer_verified=True,model_loaded=False,GPU_calls=0)))
'''


def runtime_import(root):
    root=Path(root).resolve()
    r=subprocess.run([sys.executable,'-I','-c',SCRIPT,str(root)],cwd=root,
        env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'},capture_output=True,text=True,timeout=60)
    if r.returncode:raise RuntimeError('E105 fresh-extract import failed: '+r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])
