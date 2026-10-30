"""Frozen PCA-1 vectors plus a minimal variant of the exact sealed E80c source."""
import argparse,hashlib,json,subprocess,sys,tarfile,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'results/g_agreement/understand/e112'
BASE_ARCHIVE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e80c_9b61555d_v2_ready/source.tar.gz')
BASE_SHA='d10d1a3856d63c7603864250c93a1047f0fd0eb66cdb537315f7bb08524df365'
OLD_INPUTS=BASE_ARCHIVE.parent/'inputs.tar.gz'
OLD_INPUT_SHA='56cf8976f5cc4814733e2a400319dd438ee2afa7157626188fdfb1cd109fa96b'
K_SHA='5357620cf4821ea0b910e75fe8e95b38883977237b49bfa4b54394afb9ba707e'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')


def selection(path):
    if sha(path)!=K_SHA:raise ValueError('immutable committed1451a11f K_SELECTION identity')
    k=read(path)
    if k['k']!=1 or not k['pca_k_share']>=k['j_share_pooled'] or round(k['j_share_pooled'],4)!=.1431:
        raise ValueError('original all518 pooled minimum k1')
    return k


def transform(h,q):
    """Original E80c arithmetic and per-site mean; only q has one column."""
    x=np.asarray(h,np.float64);mu=x.mean(axis=0);q=np.asarray(q,np.float64)
    if h.ndim!=2 or q.shape!=(h.shape[1],1) or not np.isfinite(x).all() or not np.isfinite(q).all():raise ValueError('finite PC1/site dimensions')
    centred=x-mu;projected=(centred@q)@q.T;out=(x-projected).astype(np.float32)
    denominator=float(np.sum(centred*centred));norm=np.linalg.norm(x,axis=1)
    if denominator<=0 or np.any(norm==0):raise ValueError('nonzero centred variance/norms')
    ratios=np.linalg.norm(out.astype(np.float64),axis=1)/norm
    return out,mu,dict(variance_removed=float(np.sum(projected*projected)/denominator),
       norm_ratios=ratios.tolist(),variance_definition='pooled sum||P1(h-mu_site)||^2 / sum||h-mu_site||^2',
       norm_definition='actual saved float32 ||h_prime|| / original ||h||')


def payload():
    if sha(BASE_ARCHIVE)!=BASE_SHA:raise ValueError('original E80c source archive identity')
    with tarfile.open(BASE_ARCHIVE) as t:files={m.name:t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
    for n,h in json.loads(files['results/g_agreement/understand/e80c/DEPENDENCIES.json']).items():
        if hashlib.sha256(files[n]).hexdigest()!=h:raise ValueError('original E80c dependency identity')
    return files


def vectors(out):
    k=selection(HERE/'K_SELECTION.json');capture=k['inputs']['capture_seal'];cap_path=Path(capture['path'])
    if sha(cap_path)!=capture['sha256']:raise ValueError('original capture seal')
    cap=read(cap_path)
    for n,h in cap['files'].items():
        if sha(cap_path.parent/n)!=h:raise ValueError('original capture member')
    basis_path=Path(k['inputs']['PCA384']['path']);j_path=Path(k['inputs']['J384']['path'])
    if sha(basis_path)!=k['inputs']['PCA384']['sha256'] or sha(j_path)!=k['inputs']['J384']['sha256']:raise ValueError('original PCA/J basis')
    e80c_seal=basis_path.parent/'RESULT_SEAL.json'
    if sha(e80c_seal)!=k['inputs']['e80c_result_seal']:raise ValueError('original E80c vector seal')
    for name,digest in read(e80c_seal)['files'].items():
        if sha(e80c_seal.parent/name)!=digest:raise ValueError('original E80c vector member')
    basis=np.load(basis_path,allow_pickle=False).astype(np.float64);q=basis[:,:1]
    if basis.shape!=(5120,384) or not np.isclose(float((q.T@q)[0,0]),1.,atol=1e-6):raise ValueError('sealed orthonormal PC1')
    h={b:np.load(cap_path.parent/f'acts{b}.npy',allow_pickle=False) for b in (44,42)}
    if any(x.shape!=(518,5120) or x.dtype!=np.float32 for x in h.values()):raise ValueError('518 original float32 captures at both sites')
    if sha(cap_path.parent/'acts44.npy')!=k['inputs']['acts44']['sha256']:raise ValueError('acts44 freeze')
    centred=h[44].astype(np.float64)-h[44].astype(np.float64).mean(axis=0);den=float(np.sum(centred*centred))
    eigenvalues=np.maximum(np.linalg.eigvalsh(centred@centred.T)[::-1],0)
    cumulative=np.minimum(np.cumsum(eigenvalues)/den,1.).tolist()
    j=np.load(j_path,allow_pickle=False).astype(np.float64)
    j_share=float(np.sum((centred@j)**2)/den)
    if not np.isclose(j_share,k['j_share_pooled'],atol=1e-9) or not np.isclose(cumulative[0],k['pca_k_share'],atol=1e-7):raise ValueError('frozen pooled rank arithmetic')
    if not cumulative[0]>=j_share:raise ValueError('k1 must cross J share')
    if sha(OLD_INPUTS)!=OLD_INPUT_SHA:raise ValueError('original E80c public item packet')
    with tarfile.open(OLD_INPUTS) as t:
        item_member=next(m for m in t.getmembers() if m.name.endswith('/items.json'))
        item_bytes=t.extractfile(item_member).read();items=json.loads(item_bytes)
    ids=read(cap_path.parent/'items.order.json')
    if len(items)!=518 or [x['id'] for x in items]!=ids or any(set(x)!={'id','feature'} for x in items):raise ValueError('exact original518 public order')
    out.mkdir(parents=True,exist_ok=False);v=out/'vectors';v.mkdir();public=out/'inputs';public.mkdir()
    diagnostics={}
    for b,reader in ((44,'oracle'),(42,'nla')):
        result,mu,d=transform(h[b],q);np.save(v/f'PCA1_ablated{b}.npy',result,allow_pickle=False)
        np.save(v/f'mu{b}.npy',mu,allow_pickle=False);diagnostics[reader]=d
        (public/f'PCA1_ablated{b}.npy').write_bytes((v/f'PCA1_ablated{b}.npy').read_bytes())
    np.save(v/'PCA1.npy',q,allow_pickle=False)
    projection=dict(experiment='E112',k=1,n=518,basis_block=44,centred=True,same_e80c_mu_and_basis=True,
      cumulative_variance=cumulative,J_variance_share=j_share,k_selection_sha256=K_SHA,
      source_capture_sha256=capture['sha256'],source_PCA384_sha256=k['inputs']['PCA384']['sha256'],
      source_J384_sha256=k['inputs']['J384']['sha256'],mean_recipe='per-block float64 mean across all518, exactly E80c build.py',
      basis_recipe='column0 of sealed PCA384.npy, promoted float64; no refit, renormalization or QR')
    write(v/'PROJECTION.json',projection);write(v/'DIAGNOSTICS.json',diagnostics)
    write(v/'VECTOR_SEAL.json',dict(experiment='E112',k=1,n_items=518,n_vectors=1036,source_capture_sha256=capture['sha256'],
      k_selection_sha256=K_SHA,conditions=['PCA1_ablated'],exploratory_block42_uses_block44_basis=True,
      files={p.name:sha(p) for p in v.iterdir()}))
    (public/'items.json').write_bytes(item_bytes)
    write(public/'PLAN.json',dict(experiment='E112',conditions=['PCA1_ablated'],capture_seal_sha256=capture['sha256'],
      vector_seal_sha256=sha(v/'VECTOR_SEAL.json'),item_ids=ids,k=1,k_selection_sha256=K_SHA,basis_block=44,
      original_E80c_result_seal=k['inputs']['e80c_result_seal'],none_regenerated=False))
    seeds=dict(oracle_setup=347.7268692100188,nla_setup=293.8343498230679,oracle_native=11.115151894329067,nla_native=19.17773307699612)
    write(public/'STAGE_REQUEST.json',dict(experiment='E112',status='HOLD_INTEGRATOR_ADMISSION',cap_seconds=None,
      cumulative_cap_seconds=None,account_gate_USD=900,seed_seconds_per_batch=seeds))
    write(public/'INPUT_SEAL.json',dict(experiment='E112',labels_on_pod=False,files={p.name:sha(p) for p in public.iterdir()}))
    archive=out/'inputs.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for p in public.iterdir():t.add(p,arcname='inputs/'+p.name,recursive=False)
    return dict(experiment='E112',input_root=str(public),input_sha256=sha(public/'INPUT_SEAL.json'),archive=str(archive),
      archive_sha256=sha(archive),vector_root=str(v),vector_seal_sha256=sha(v/'VECTOR_SEAL.json'),
      k=1,PCA1_share=diagnostics['oracle']['variance_removed'],J_share=j_share,labels_on_pod=False,
      stage_request_status='HOLD_INTEGRATOR_ADMISSION',reader_calls=0,GPU_calls=0)

def bind_stage(inputs,input_sha,out,cap,cumulative,gate):
    import shutil
    if sha(inputs/'INPUT_SEAL.json')!=input_sha:raise ValueError('original public input seal')
    seal=read(inputs/'INPUT_SEAL.json')
    for name,digest in seal['files'].items():
        if sha(inputs/name)!=digest:raise ValueError('original public input member')
    if cap<=0 or cumulative<cap or gate<=0:raise ValueError('positive admitted cap/cumulative/gate')
    out.mkdir(parents=True,exist_ok=False)
    for name in seal['files']:
        if name!='STAGE_REQUEST.json':shutil.copyfile(inputs/name,out/name)
    limits=read(inputs/'STAGE_REQUEST.json');limits.update(status='READY',cap_seconds=cap,cumulative_cap_seconds=cumulative,account_gate_USD=gate)
    write(out/'STAGE_REQUEST.json',limits)
    write(out/'INPUT_SEAL.json',dict(experiment='E112',labels_on_pod=False,files={p.name:sha(p) for p in out.iterdir()}))
    return dict(input_root=str(out),input_sha256=sha(out/'INPUT_SEAL.json'),original_input_sha256=input_sha,vector_bytes_unchanged=True)


PREFLIGHT=r'''
import importlib,inspect,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(root),str(root/'results/g_agreement/understand/e112'),str(root/'results/g_agreement/understand/late198'),str(root/'results/g_agreement/understand/e56/job')]
import common,worker112,runtime,worker56
from projects.g_agreement.blindspot import run
r=runtime.Runtime(Path('/NOT_READ_CPU/assets.json'))
assert r.model is None and r.readers is None and r.tok is None
for module in (common,worker112,runtime,worker56,run):
    assert Path(module.__file__).resolve().is_relative_to(root)
assert worker112.CONDITIONS==('PCA1_ablated',)
assert callable(run._load_oracle) and callable(worker56.Backend.load_nla)
print(json.dumps(dict(status='PASS',runtime_imported=True,worker56_imported=True,common_imported=True,model_loaded=False,GPU_calls=0)))
'''


def package(out):
    files=payload()
    for p in (ROOT/'common').rglob('*'):
        if p.is_file() and p.suffix in ('.py','.sh'):files[str(p.relative_to(ROOT))]=p.read_bytes()
    for p in (ROOT/'projects/g_agreement/e112_runner').glob('*.py'):files[str(p.relative_to(ROOT))]=p.read_bytes()
    files['results/g_agreement/understand/e112/K_SELECTION.json']=(HERE/'K_SELECTION.json').read_bytes()
    dep={n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())}
    (HERE/'DEPENDENCIES.json').write_text(json.dumps(dep,indent=2)+'\n')
    for name in ('worker112.py','test_worker112.py','DEPENDENCIES.json'):files['results/g_agreement/understand/e112/'+name]=(HERE/name).read_bytes()
    seal=dict(experiment='E112',original_E80c_archive_sha256=BASE_SHA,files={n:sha(HERE/n) for n in ('worker112.py','test_worker112.py','DEPENDENCIES.json')})
    (HERE/'SOURCE_SEAL.json').write_text(json.dumps(seal,indent=2)+'\n')
    files['results/g_agreement/understand/e112/SOURCE_SEAL.json']=(HERE/'SOURCE_SEAL.json').read_bytes()
    out.mkdir(parents=True,exist_ok=False);archive=out/'source.tar.gz'
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        for n,b in files.items():p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        check=subprocess.run([sys.executable,'-I','-c',PREFLIGHT,str(root)],cwd=root,capture_output=True,text=True,timeout=60)
        if check.returncode:raise RuntimeError(check.stderr[-3000:])
        with tarfile.open(archive,'w:gz',compresslevel=1) as t:
            for n in sorted(files):t.add(root/n,arcname=n,recursive=False)
    receipt=dict(experiment='E112',source_archive=str(archive),source_archive_sha256=sha(archive),
      source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),original_E80c_archive_sha256=BASE_SHA,
      preflight=json.loads(check.stdout.strip().splitlines()[-1]),native_adapter_and_clock_bytes_unchanged=True,
      labels_on_pod=False,GPU_calls=0,reader_calls=0)
    write(out/'PACKAGE.json',receipt);return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['vectors','source','bind']);p.add_argument('--out',type=Path,required=True);p.add_argument('--inputs',type=Path);p.add_argument('--input-sha');p.add_argument('--cap-seconds',type=int);p.add_argument('--cumulative-cap-seconds',type=int);p.add_argument('--account-gate-usd',type=float,default=900);a=p.parse_args()
    if a.mode=='bind':
        if not a.inputs or not a.input_sha or a.cap_seconds is None:p.error('bind requires --inputs --input-sha --cap-seconds')
        result=bind_stage(a.inputs,a.input_sha,a.out,a.cap_seconds,a.cumulative_cap_seconds or a.cap_seconds,a.account_gate_usd)
    else:result=vectors(a.out) if a.mode=='vectors' else package(a.out)
    print(json.dumps(result,indent=2))
