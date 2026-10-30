"""Container-local fixed-wheel installation; no scientific package or shared writes."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path

ALLOWED={'tilelang','apache-tvm-ffi','torch-c-dlpack-ext','cloudpickle','ml-dtypes','psutil','tqdm','typing-extensions','z3-solver'}


def verify_wheels(manifest,wheelhouse):
    d=json.loads(Path(manifest).read_text())
    if set(d['pins'])!=ALLOWED:raise ValueError('exact optional-backend dependency allowlist')
    for p in d['pins'].values():
        w=p['wheels']['linux'];f=Path(wheelhouse)/w['filename']
        if hashlib.sha256(f.read_bytes()).hexdigest()!=w['sha256']:raise ValueError('wheel hash '+f.name)
    return d


def install(manifest,wheelhouse,root,base_python):
    root=root.resolve()
    if not root.is_relative_to(Path('/workspace')) or root==Path('/workspace') or root.exists():raise ValueError('new container-local /workspace child only')
    d=verify_wheels(manifest,wheelhouse);root.mkdir(parents=True);overlay=root/'site';lock=root/'requirements.lock'
    lock.write_text('\n'.join(n+'=='+p['version']+' --hash=sha256:'+p['wheels']['linux']['sha256'] for n,p in d['pins'].items())+'\n')
    env=dict(os.environ,PIP_CACHE_DIR=str(root/'pip-cache'),PYTHONDONTWRITEBYTECODE='1',PYTHONPYCACHEPREFIX=str(root/'pycache'))
    cmd=[str(base_python),'-m','pip','install','--disable-pip-version-check','--no-index','--no-deps','--require-hashes','--find-links',str(wheelhouse),'--target',str(overlay),'-r',str(lock)]
    with (root/'INSTALL.log').open('w') as f:subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    result={'status':'PINNED_OPTIONAL_BACKEND_OVERLAY_INSTALLED','overlay':str(overlay),'base_python':str(base_python),'shared_runtime_mutated':False,'manifest_sha256':hashlib.sha256(Path(manifest).read_bytes()).hexdigest()}
    (root/'INSTALL_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('manifest','wheelhouse','root','base-python'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();install(a.manifest,a.wheelhouse,a.root,a.base_python)
