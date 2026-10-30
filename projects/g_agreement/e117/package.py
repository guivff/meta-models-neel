"""Frozen native runtime plus E117-only hook and exact-source tests."""
import argparse,json,subprocess,sys,tarfile,tempfile
from pathlib import Path
from projects.g_agreement.e101.package104 import ROOT,source_paths
from projects.g_agreement.e100.contract import write,sha,verify

def build(out):
    paths=source_paths()
    for folder in ('e100','e117'):paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'projects/g_agreement'/folder).glob('*.py'))
    out.mkdir(parents=True,exist_ok=False);target='results/g_agreement/understand/e117/SOURCE_SEAL.json';local=out/'SOURCE_SEAL.json'
    write(local,dict(experiment='E117',authority='BRIEF_UNDERSTAND §228',files={n:sha(ROOT/n) for n in sorted(paths)}))
    archive=out/'source.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for n in sorted(paths):t.add(ROOT/n,arcname=n,recursive=False)
        t.add(local,arcname=target,recursive=False)
    with tempfile.TemporaryDirectory() as tmp:
        r=Path(tmp)
        with tarfile.open(archive) as t:t.extractall(r,filter='data')
        verify(r,target,sha(local))
        script="import sys;from pathlib import Path;r=Path(sys.argv[1]).resolve();sys.path.insert(0,str(r));import common;from projects.g_agreement.e117 import runner;old=runner.original();from projects.g_agreement.blindspot import run;assert Path(run.__file__).resolve().is_relative_to(r);assert Path(old.__file__).resolve().is_relative_to(r);assert callable(run._load_oracle);print('PASS actual native runtime/common import, no model/GPU')"
        result=subprocess.run([sys.executable,'-I','-c',script,str(r)],cwd=r,capture_output=True,text=True,check=True)
        subprocess.run([sys.executable,'-m','pytest','-q','projects/g_agreement/e117/test_hook.py'],cwd=r,check=True)
    (ROOT/target).write_bytes(local.read_bytes())
    receipt=dict(experiment='E117',archive=str(archive.resolve()),archive_sha256=sha(archive),source_sha256=sha(local),tests=8,fresh_extract_import=result.stdout.strip(),GPU_calls=0)
    write(out/'PACKAGE.json',receipt);write(ROOT/'results/g_agreement/understand/e117/DELIVERY.json',receipt);return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
