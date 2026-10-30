"""Exact-source fresh-extract runtime import and synthetic tests; no pod action."""
import argparse,json,tarfile,tempfile,subprocess,sys,os
from pathlib import Path
from projects.g_agreement.e101.package104 import source_paths,ROOT
from projects.g_agreement.e100.contract import write,sha,verify
SCRIPT='''import sys\nfrom pathlib import Path\nr=Path(sys.argv[1]).resolve();sys.path.insert(0,str(r))\nimport common\nfrom projects.g_agreement.e100e import runner\nm=runner.original()\nfrom projects.g_agreement.blindspot import run\nfor obj in (common,runner,m,sys.modules[m.Backend.__module__],run):assert Path(obj.__file__).resolve().is_relative_to(r)\nassert callable(m.Backend.native_one) and callable(run._load_oracle)\nprint("PASS actual E79/worker56/native runtime imports, no model/GPU")\n'''
def build(out):
    paths=source_paths()
    for folder in ('e100','e100e'):paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'projects/g_agreement'/folder).glob('*.py'))
    out.mkdir(parents=True,exist_ok=False);target='results/g_agreement/understand/e100e/SOURCE_SEAL.json';local=out/'SOURCE_SEAL.json'
    write(local,dict(experiment='E100e',authority=['14e408dcf','f599f121a2addd54fa2f1f2039bbe31d83e1267d'],lineage='E100 a / E79 8e431cca',files={n:sha(ROOT/n) for n in sorted(paths)}))
    archive=out/'source.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for n in sorted(paths):t.add(ROOT/n,arcname=n,recursive=False)
        t.add(local,arcname=target,recursive=False)
    with tempfile.TemporaryDirectory() as tmp:
        r=Path(tmp)
        with tarfile.open(archive) as t:t.extractall(r,filter='data')
        verify(r,target,sha(local))
        result=subprocess.run([sys.executable,'-I','-c',SCRIPT,str(r)],cwd=r,env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'},capture_output=True,text=True,timeout=60)
        if result.returncode:raise RuntimeError(result.stderr[-3000:])
        subprocess.run([sys.executable,'-m','pytest','-q','projects/g_agreement/e100e/test_runner.py'],cwd=r,check=True)
    (ROOT/target).write_bytes(local.read_bytes())
    receipt=dict(experiment='E100e',archive=str(archive.resolve()),archive_sha256=sha(archive),source_seal=target,source_sha256=sha(local),fresh_extract_import=result.stdout.strip(),synthetic_tests=14,GPU_calls=0)
    write(out/'PACKAGE.json',receipt);return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
