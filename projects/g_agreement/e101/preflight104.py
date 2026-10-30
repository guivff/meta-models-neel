"""Fresh-process import rehearsal for the exact extracted E104 runtime."""
import json,os,subprocess,sys
from pathlib import Path

SCRIPT=r'''
import importlib,inspect,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
import common
from projects.g_agreement.blindspot import run as native
from projects.g_agreement.e101.runner import dependencies
from projects.g_agreement.e101 import runner104
from projects.g_agreement.e104_vectors import build as vectors
_,Runtime,_,_,_=dependencies()
runtime=Runtime(Path('/NOT_READ_CPU_PREFLIGHT/assets.json'))
assert runtime.model is None and runtime.tok is None and runtime.readers is None
modules={'common':common,'blindspot.run':native,'runner104':runner104,'vector_capture':vectors,'runtime':sys.modules[Runtime.__module__]}
paths={}
for name,module in modules.items():
    path=Path(module.__file__).resolve()
    assert path.is_relative_to(root),name+' imported outside extracted source'
    paths[name]=str(path.relative_to(root))
assert callable(native._assets) and callable(native._load_oracle) and callable(vectors.capture_once)
print(json.dumps(dict(status='PASS',runtime_imports=paths,model_loaded=False,GPU_calls=0)))
'''


def runtime_import(root,python=None):
    root=Path(root).resolve()
    result=subprocess.run([python or sys.executable,'-I','-c',SCRIPT,str(root)],cwd=root,
        env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'},capture_output=True,text=True,timeout=60)
    if result.returncode:raise RuntimeError('E104 extracted runtime import failed: '+result.stderr[-3000:])
    return json.loads(result.stdout.strip().splitlines()[-1])
