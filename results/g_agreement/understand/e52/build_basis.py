"""One CPU-only execution of Suraj's registered layer44 J-space construction."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CACHE=ROOT/'cache/g_agreement/understand/e52'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def read(p):return json.loads(Path(p).read_text())
def dump(p,obj):Path(p).write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')

def main():
    import numpy as np
    import torch
    from safetensors import safe_open
    inputs=read(HERE/'BASIS_INPUTS_2026-10-27.json')
    for item in inputs['files'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('basis input hash mismatch')
    for name,h in inputs['source_files'].items():
        if sha(ROOT/name)!=h:raise ValueError('basis source drift')
    CACHE.mkdir(parents=True,exist_ok=True)
    with (CACHE/'BASIS_BUILD_CLAIM.json').open('x') as f:
        json.dump({'status':'CLAIMED_NEVER_RESET','created_epoch':time.time(),'input_manifest_sha256':sha(HERE/'BASIS_INPUTS_2026-10-27.json'),'pid':os.getpid()},f)
    torch.set_num_threads(8)
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.jspace import load_jlens_layers,jspace_basis
    t=time.time()
    j=load_jlens_layers(inputs['files']['jlens']['path'],[44])[44]
    with safe_open(inputs['files']['unembedding_shard']['path'],framework='pt',device='cpu') as f:
        wu=f.get_tensor('lm_head.weight')
    with safe_open(inputs['files']['norm_shard']['path'],framework='pt',device='cpu') as f:
        w=f.get_tensor('model.language_model.norm.weight').float()
    gain=1+w
    if j.shape!=(5120,5120) or wu.shape!=(248320,5120) or gain.shape!=(5120,):raise ValueError('registered tensor shapes required')
    if any(x.device.type!='cpu' or not torch.isfinite(x).all() for x in (j,wu,gain)):raise ValueError('finite CPU tensors required')
    print('Inputs verified; constructing one block44 Gram matrix and eigendecomposition on CPU',flush=True)
    basis=jspace_basis(j,wu,gain,r_max=1536,chunk=4096,layer=44)
    q=basis.vecs.numpy();evals=basis.evals.numpy()
    error=float(np.max(np.abs(q.astype(np.float64).T@q.astype(np.float64)-np.eye(1536))))
    if error>1e-5 or not np.isfinite(q).all() or np.any(evals<=0) or np.any(np.diff(evals)>0):raise ValueError('basis validity failure; do not retry')
    np.save(CACHE/'basis_L44_r1536.npy',q,allow_pickle=False)
    np.save(CACHE/'squared_singular_values_L44.npy',evals,allow_pickle=False)
    rng=np.random.default_rng(20261027);directions=rng.normal(size=(200,5120));directions/=np.linalg.norm(directions,axis=1,keepdims=True)
    np.save(CACHE/'random_unit_directions.npy',directions,allow_pickle=False)
    null={}
    for r in (384,1536):
        x=np.square(directions@q[:,:r].astype(np.float64)).sum(axis=1)/(r/5120)
        null[str(r)]={'values':x.tolist(),'mean':float(x.mean()),'sample_sd':float(x.std(ddof=1))}
    dump(CACHE/'ENRICHMENT_NULL.json',{'seed':20261027,'n':200,'ranks':null})
    files={n:sha(CACHE/n) for n in ('basis_L44_r1536.npy','squared_singular_values_L44.npy','random_unit_directions.npy','ENRICHMENT_NULL.json')}
    receipt={'experiment':'E52','status':'SEALED','layer':44,'ranks':[384,1536],'device':'cpu','matrix':'W_U @ diag(1+w) @ J_44','first_5_singular_values':np.sqrt(evals[:5].astype(np.float64)).tolist(),'orthonormality_max_abs_error':error,'elapsed_seconds':time.time()-t,'files':files,'input_manifest_sha256':sha(HERE/'BASIS_INPUTS_2026-10-27.json'),'basis_builds':1,'source_citation':inputs['source_citation'],'created_epoch':time.time()}
    dump(CACHE/'BASIS_SEAL.json',receipt);dump(HERE/'BASIS_SEAL_2026-10-27.json',receipt)
    print(json.dumps({'status':'SEALED','first_5_singular_values':receipt['first_5_singular_values'],'basis_sha256':files['basis_L44_r1536.npy'],'seconds':receipt['elapsed_seconds']}),flush=True)

if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('No overrides; run the sealed basis command once')
    main()
