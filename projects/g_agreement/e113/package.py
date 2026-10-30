"""Seal native runtime/capture source and rehearse isolated imports before create."""
import argparse,json,tarfile,tempfile,subprocess,sys,os
from pathlib import Path
from projects.g_agreement.e101.package104 import source_paths,ROOT
from projects.g_agreement.e101.contract import write,sha,verify
SCRIPT=r'''
import sys,json
from pathlib import Path
root=Path(sys.argv[1]).resolve();sys.path[:0]=[str(root),str(root/'results/g_agreement/understand/late198')]
import common
from projects.g_agreement.blindspot import run
from projects.g_agreement.e101.runner import dependencies
from projects.g_agreement.e113 import capture,runner
_,Runtime,_,_,_=dependencies();r=Runtime(Path('/NOT_READ/assets.json'))
assert r.model is None and r.readers is None and r.tok is None
for m in (common,run,capture,runner,sys.modules[Runtime.__module__]):assert Path(m.__file__).resolve().is_relative_to(root)
assert callable(capture.capture_lens) and callable(run._load_oracle)
print(json.dumps(dict(status='PASS',native_runtime=True,model_loaded=False,GPU_calls=0)))
'''

def build(out):
    paths=source_paths();paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'projects/g_agreement/e113').glob('*.py'))
    out.mkdir(parents=True,exist_ok=False);local=out/'SOURCE_SEAL.json';target='results/g_agreement/understand/e113/SOURCE_SEAL.json'
    write(local,dict(experiment='E113',authority='14e408dcf',files={p:sha(ROOT/p) for p in sorted(paths)}))
    archive=out/'source.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for name in sorted(paths):t.add(ROOT/name,arcname=name,recursive=False)
        t.add(local,arcname=target,recursive=False)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        with tarfile.open(archive) as t:t.extractall(root,filter='data')
        verify(root,target,sha(local))
        check=subprocess.run([sys.executable,'-I','-c',SCRIPT,str(root)],cwd=root,env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'},capture_output=True,text=True,timeout=60)
        if check.returncode:raise RuntimeError(check.stderr[-3000:])
        subprocess.run([sys.executable,'-m','pytest','-q','projects/g_agreement/e113/test_capture.py'],cwd=root,check=True)
    (ROOT/target).write_bytes(local.read_bytes())
    result=dict(experiment='E113',archive=str(archive),archive_sha256=sha(archive),source_seal=target,source_sha256=sha(local),tests=5,fresh_extract_import=json.loads(check.stdout.strip().splitlines()[-1]),GPU_calls=0)
    write(out/'PACKAGE.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
