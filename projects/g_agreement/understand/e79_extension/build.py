"""E79 added states only; reuse original dev-direction and injection functions."""
import importlib.util
import subprocess
import time
from pathlib import Path
import numpy as np
from projects.g_agreement.readerbench.io import read,write,sha,verify,seal_output
from projects.g_agreement.readerbench.scoring import require
ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'results/g_agreement/understand/e79_extension'
ROWS=('user_expertise','unit_system')


def load_original(spec):
    p=Path(spec['original_builder']);require(sha(p)==spec['files'][str(p)],'original E79 implementation pin')
    s=importlib.util.spec_from_file_location('_original_e79',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return m


def fit_row(meta,order,acts,row,values,original,q,index):
    by={m['id']:m for m in meta};require(len(by)==len(meta),'unique metadata IDs')
    groups={split:{value:sorted(k for k in order if by[k]['feature']==row and by[k]['split']==split and by[k]['value']==value) for value in values} for split in ('dev','test')}
    require(all(len(g)==42 for split in groups.values() for g in split.values()),'42/42 dev and test')
    ix={k:i for i,k in enumerate(order)};require(len(ix)==len(order),'unique capture IDs')
    means=np.stack([np.stack([acts[ix[k]] for k in groups['dev'][v]]).mean(0,dtype=np.float64) for v in values])
    d,u,f=original.directions(means,q,np.random.default_rng(np.random.SeedSequence([20261028,index,0])))
    ids=sorted(groups['test'][values[0]]+groups['test'][values[1]])
    h=np.asarray([acts[ix[k]] for k in ids],float)
    targets=np.random.default_rng(np.random.SeedSequence([20261028,index,1])).permutation(np.array([1]*42+[-1]*42))
    return ids,h,means,d,u,f,targets


def run():
    started=time.monotonic();plan=HERE/'INPUTS.json';spec=read(plan)
    require(subprocess.check_output(['git','show','HEAD:'+str(plan.relative_to(ROOT))],cwd=ROOT)==plan.read_bytes(),'commit inputs before compute')
    for p,h in spec['files'].items():require(sha(p)==h,'frozen source hash')
    for p,h in spec['seals'].items():verify(p,h)
    original=load_original(spec);q=np.asarray(np.load(spec['basis'],allow_pickle=False),float)
    if q.shape==(384,5120):q=q.T
    require(q.shape==(5120,384) and np.max(np.abs(q.T@q-np.eye(384)))<1e-4,'same sealed rank384 J basis')
    meta=read(spec['metadata']);order=read(spec['order']);acts=np.load(spec['acts44'],mmap_mode='r',allow_pickle=False)
    require(acts.shape==(len(order),5120),'block44 capture grid')
    private=ROOT/'cache/g_agreement/understand/e79_extension';private.mkdir(parents=True,exist_ok=False);private.chmod(0o700)
    require(subprocess.run(['git','check-ignore','-q',str(private/'KEY.DO_NOT_SHARE.json')],cwd=ROOT).returncode==0,'private map ignored')
    pod=HERE/'pod_inputs';pod.mkdir(exist_ok=False);vectors=[];public=[];key=[];cpu={};reports=[]
    by={m['id']:m for m in meta}
    for offset,row in enumerate(ROWS):
        ri=5+offset # Append fresh streams after all five original E79 states.
        values=spec['values'][row]
        ids,h,means,d,u,f,signs=fit_row(meta,order,acts,row,values,original,q,ri)
        rng=np.random.default_rng(np.random.SeedSequence([20261028,ri,2]));cells=[('baseline',0,h)]
        cells += [(name,a,original.injection(h,d,u[i],signs,a)) for a in (1,2,4,.25,.5) for i,name in enumerate(('J','nonJ','random'))]
        diagnostics=[]
        for name,a,v in cells:
            saved=v.astype(np.float32);require(np.isfinite(saved).all(),'finite public vectors')
            ratios=np.linalg.norm(saved.astype(float),axis=1)/np.linalg.norm(h,axis=1)
            diagnostics.append(dict(condition=name,alpha=a,n=84,norm_ratio_min=float(ratios.min()),norm_ratio_max=float(ratios.max()),norm_ratio_mean=float(ratios.mean()),above_1_5=int((ratios>1.5).sum()),per_item=ratios.tolist()))
            for i,ident in enumerate(ids):
                oid=rng.bytes(16).hex();public.append(dict(id=oid,index=len(vectors),row=row,arm='A',condition=name,alpha=a,block=44));vectors.append(saved[i])
                key.append(dict(id=oid,source_item_id=ident,row=row,arm='A',condition=name,alpha=a,true_label=int(by[ident]['value']==values[0]),target_label=int(signs[i]>0),sign=int(signs[i])))
        cpu[row+'__means']=means;cpu[row+'__mu']=means.mean(0);cpu[row+'__d']=d;cpu[row+'__unit_directions']=u
        reports.append(dict(row=row,J_fraction=f,d_norm=float(np.linalg.norm(d)),rng_row_index=ri,cells=diagnostics))
    require(len(vectors)==2688 and len({x['id'] for x in public})==2688,'two new states x16cells x84')
    np.save(pod/'INPUT_VECTORS.npy',np.asarray(vectors,np.float32),allow_pickle=False);write(pod/'ITEMS.json',public)
    write(private/'KEY.DO_NOT_SHARE.json',key);(private/'KEY.DO_NOT_SHARE.json').chmod(0o600)
    np.savez(private/'CPU_DIRECTIONS.npz',**cpu);(private/'CPU_DIRECTIONS.npz').chmod(0o600)
    seal_output(pod,dict(experiment='E79_extension',status='SEALED_INPUTS_NO_READERS',n=2688,layer=44,input_spec_sha256=sha(plan),states=list(ROWS)))
    write(HERE/'DIAGNOSTICS.json',dict(rows=reports,exclusions_applied=False,original_states_recomputed=False))
    write(HERE/'BUILD_RECEIPT.json',dict(status='READY',n_vectors=2688,n_cells=32,pod_seal_sha256=sha(pod/'RESULT_SEAL.json'),private_map_sha256=sha(private/'KEY.DO_NOT_SHARE.json'),cpu_directions_sha256=sha(private/'CPU_DIRECTIONS.npz'),input_spec_sha256=sha(plan),wall_seconds=time.monotonic()-started,gpu_hours=0,reader_calls=0))
    seal_output(HERE,dict(experiment='E79_extension',status='READY_NEW_STATES_ONLY'))
    print('E79 extension: 2688 vectors sealed; no reader calls.')

if __name__=='__main__':run()
