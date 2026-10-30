"""§169 amendment1: sparse J-fraction label of record; reuse sealed G3 and SVD."""
from pathlib import Path
import json
import sys
import time
import numpy as np
from build_basis import ROOT,HERE,CACHE,sha,read,dump
from run_labels import verify

def fraction(h,reconstruction):
    x=np.asarray(h,dtype=np.float64);r=np.asarray(reconstruction,dtype=np.float64)
    if x.shape!=r.shape or x.ndim!=2 or not np.isfinite(x).all() or not np.isfinite(r).all() or np.any(np.square(x).sum(1)==0):raise ValueError('finite nonzero directions and reconstructions required')
    return np.square(r).sum(1)/np.square(x).sum(1)

def primary_label(value,median,upper,g3):
    if value>=upper and (g3.get('readable') is True or g3['status']=='NOT EVALUABLE'):return 'IN-J'
    if value<=median and g3.get('readable') is not True:return 'OUT-J'
    return 'DIFFUSE'

def run():
    import torch
    from safetensors import safe_open
    verify(ROOT,read(HERE/'SPARSE_CODE_SEAL_2026-10-27.json')['files'])
    basis=read(HERE/'BASIS_SEAL_2026-10-27.json');verify(CACHE,basis['files'])
    inputs=read(HERE/'BASIS_INPUTS_2026-10-27.json')
    for name in ('jlens','unembedding_shard'):
        if sha(inputs['files'][name]['path'])!=inputs['files'][name]['sha256']:raise ValueError('pinned weights differ')
    with (CACHE/'SPARSE_PRIMARY_ONCE.json').open('x') as f:json.dump({'status':'CLAIMED_NEVER_RESET','epoch':time.time()},f)
    out=CACHE/'sparse-primary';out.mkdir(exist_ok=False);torch.set_num_threads(8);started=time.time()
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.jspace import load_jlens_layers,jlens_atoms,nn_pursuit
    j=load_jlens_layers(inputs['files']['jlens']['path'],[44])[44]
    with safe_open(inputs['files']['unembedding_shard']['path'],framework='pt',device='cpu') as f:wu=f.get_tensor('lm_head.weight')
    print('Building unit W_U J44 atoms on CPU, without final-norm gain',flush=True)
    atoms,norms=jlens_atoms(j,wu,torch.ones(5120),chunk=4096)
    torch.save({'atoms':atoms,'norms':norms,'layer':44,'map':'W_U @ J44'},out/'atoms.pt')
    dump(out/'ATOM_SEAL.json',{'files':{'atoms.pt':sha(out/'atoms.pt')},'source_weights':{k:inputs['files'][k]['sha256'] for k in ('jlens','unembedding_shard')},'map':'W_U @ J44','normalised':True,'dtype':'bfloat16','k':16,'refine_steps':6,'cpu_only':True})
    del wu,j
    random=np.load(CACHE/'random_unit_directions.npy',allow_pickle=False).astype(np.float32)
    print('Pursuing200 sealed random directions, k16, CPU only',flush=True)
    idx,coef,rec=nn_pursuit(torch.from_numpy(random),atoms,k=16)
    null=fraction(random,rec.numpy());middle,upper=np.quantile(null,[.5,.975])
    np.savez_compressed(out/'random_pursuit.npz',idx=idx.numpy(),coef=coef.numpy(),reconstruction=rec.numpy(),fractions=null)
    dump(out/'NULL_SEAL.json',{'files':{'random_pursuit.npz':sha(out/'random_pursuit.npz')},'random_directions_sha256':basis['files']['random_unit_directions.npy'],'median':float(middle),'percentile97_5':float(upper),'n':200,'k':16,'atom_seal_sha256':sha(out/'ATOM_SEAL.json')})
    for bank in ('E36','W1','W12'):
        rows=read(HERE/bank/'ROW_LABELS.json')['rows'];verify(HERE/bank,read(HERE/bank/'LABEL_SEAL.json')['files'])
        raw=CACHE/(bank+'-labels')
        if sha(raw/'OUTPUT_SEAL.json')!=read(HERE/bank/'ROW_LABELS.json')['raw_output_seal_sha256']:raise ValueError('secondary raw seal binding drift')
        verify(raw,read(raw/'OUTPUT_SEAL.json')['files'])
        dirs=np.load(raw/'directions.npz',allow_pickle=False);h=np.stack([dirs[x['row']] for x in rows]).astype(np.float32)
        print('Pursuing '+bank+' class-mean directions once',flush=True)
        idx,coef,rec=nn_pursuit(torch.from_numpy(h),atoms,k=16);f=fraction(h,rec.numpy())
        np.savez_compressed(out/(bank+'.npz'),directions=h,idx=idx.numpy(),coef=coef.numpy(),reconstruction=rec.numpy(),fractions=f)
        published=[]
        for old,value in zip(rows,f):
            new=primary_label(value,middle,upper,old['J_readability'])
            published.append({**old,'label':new,'secondary_SVD_label':old['label'],'disagrees_with_SVD':new!=old['label'],'J_fraction':float(value),'label_of_record':'nonnegative sparse J pursuit, k16'})
        dest=HERE/'primary'/bank;dest.mkdir(parents=True,exist_ok=False)
        dump(dest/'ROW_LABELS.json',{'experiment':'E52','bank':bank,'rows':published,'authority_commit':'4c187fda','original_secondary_label_seal_sha256':sha(HERE/bank/'LABEL_SEAL.json'),'atom_seal_sha256':sha(out/'ATOM_SEAL.json'),'null_seal_sha256':sha(out/'NULL_SEAL.json'),'pursuit_output_sha256':sha(out/(bank+'.npz')),'code_seal_sha256':sha(HERE/'SPARSE_CODE_SEAL_2026-10-27.json'),'reader_outcomes_accessed':False})
        lines=['# E52 '+bank+' primary and secondary labels','', '| Row | Primary sparse label | Secondary SVD label |','|---|---|---|']+[f"| {r['row']} | {r['label']} | {r['secondary_SVD_label']} |" for r in published]
        (dest/'LABELS.md').write_text('\n'.join(lines)+'\n')
        passed=True
        if bank=='E36':
            content=[r for r in published if r['class']=='content'];n=sum(r['label']=='IN-J' for r in content);passed=n>=7
            if len(content)!=9:raise ValueError('exact9 content rows required')
            dump(dest/'R1_SANITY.json',{'rule':'R1','label_of_record':'sparse pursuit','met':passed,'IN_J':n,'denominator':9,'threshold':7,'on_failure':'STOP; no dictionary or basis retry'})
        dump(dest/'LABEL_SEAL.json',{'files':{p.name:sha(p) for p in dest.iterdir()}})
        print(bank+' primary labels sealed; R1 '+('PASS' if passed else 'FAIL_STOP'),flush=True)
        dump(out/'RUN_STATUS.json',{'last_bank':bank,'R1_passed':passed,'wall_seconds':time.time()-started,'GPU_hours':0,'status':'STOP_R1_FAILURE' if not passed else 'IN_PROGRESS' if bank!='W12' else 'COMPLETE'})
        if not passed:return 2
    return 0

if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('No overrides; run sparse primary once')
    raise SystemExit(run())
