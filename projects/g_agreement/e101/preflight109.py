"""Isolated fresh-extract import of E109, original E87 and actual base runtime."""
import json,os,subprocess,sys
from pathlib import Path
from .preflight104 import SCRIPT as BASE
SCRIPT=BASE+'''
from projects.g_agreement.e101 import runner109,intervention104
b=runner109.backend87()
assert callable(b.sweep) and callable(b.confirm_layers)
for module in (runner109,intervention104,sys.modules[b.__module__] if b.__module__ in sys.modules else None):
    if module is not None: assert Path(module.__file__).resolve().is_relative_to(root)
assert Path(inspect.getfile(b)).resolve().is_relative_to(root)
print(json.dumps(dict(status='PASS',experiment='E109',E87_backend_imported=True,model_loaded=False,GPU_calls=0)))
'''


def runtime_import(root):
    root=Path(root).resolve()
    r=subprocess.run([sys.executable,'-I','-c',SCRIPT,str(root)],cwd=root,
       env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'},capture_output=True,text=True,timeout=60)
    if r.returncode:raise RuntimeError('E109 fresh-extract import failed: '+r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])
