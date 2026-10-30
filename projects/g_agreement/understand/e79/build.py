"""§196: CPU-only E79 vectors from sealed captures; no reader outputs."""
import hashlib,json,os,subprocess,time
from pathlib import Path
import numpy as np
from projects.g_agreement.readerbench.io import read,write,sha,verify,seal_output
from projects.g_agreement.readerbench.scoring import require
ROOT=Path(__file__).resolve().parents[4];HERE=ROOT/'results/g_agreement/understand/e79'
ROWS=('nesting_depth','indent_level','page_range_digit','format_plan','language_plan')


def directions(means,q,rng):
    d=means[0]-means[1];norm=np.linalg.norm(d);j=q@(q.T@d);perp=d-j
    require(np.isfinite(d).all() and norm>1e-8,'finite nonzero dev direction')
    r=rng.normal(size=len(d));r-=d*(r@d)/(norm*norm)
    norms=np.linalg.norm(np.stack([j,perp,r]),axis=1)
    require(np.isfinite(norms).all() and (norms>1e-8).all(),'nonzero unit directions')
    u=np.stack([j,perp,r])/norms[:,None]
    require(abs(u[2]@d)/norm<1e-10,'random orthogonal to d')
    return d,u,float(np.linalg.norm(j)/norm)


def injection(h,d,u,targets,alpha):
    return h+alpha*np.linalg.norm(d)*np.asarray(targets)[:,None]*u


def ablation(h,mu,u):
    return h-((h-mu)@u)[:,None]*u


def run():
    start=time.monotonic();plan=HERE/'INPUTS.json';s=read(plan)
    require(subprocess.check_output(['git','show','HEAD:'+str(plan.relative_to(ROOT))],cwd=ROOT)==plan.read_bytes(),'commit freeze before compute')
    for p,digest in s['files'].items():require(sha(p)==digest,'frozen source hash')
    for p,digest in s['seals'].items():verify(p,digest)
    q=np.asarray(np.load(s['basis'],allow_pickle=False),float)
    if q.shape==(384,5120):q=q.T
    require(q.shape==(5120,384) and np.isfinite(q).all(),'rank384 basis')
    error=float(np.max(np.abs(q.T@q-np.eye(384))))
    require(error<1e-4,'orthonormal sealed J basis')
    # Open only capture/metadata inputs after their entire source seals verified.
    data={}
    for bank,src in s['sources'].items():
        meta={x['id']:x for x in read(src['metadata'])};joined={}
        for cap in src['captures']:
            root=Path(cap['root']);order=read(root/cap['order']);acts=np.load(root/cap['acts'],mmap_mode='r',allow_pickle=False)
            require(acts.shape==(len(order),5120),'block44 capture grid')
            for i,ident in enumerate(order):
                require(ident not in joined,'unique capture IDs');joined[ident]=(meta[ident],acts[i])
        data[bank]=joined
    out=ROOT/'cache/g_agreement/understand/e79/inputs_v1'
    require(subprocess.run(['git','check-ignore','-q',str(out/'KEY.DO_NOT_SHARE.json')],cwd=ROOT).returncode==0,'private cache ignored')
    out.mkdir(parents=True,exist_ok=False);out.chmod(0o700)
    pod=out/'pod_inputs';pod.mkdir();vectors=[];public=[];private=[];reports=[];cpu={}
    try:
        for ri,row in enumerate(ROWS):
            bank='E57' if ri<3 else 'E59';joined=data[bank]
            groups={split:{label:sorted([k for k,(m,a) in joined.items() if m['feature']==row and m['split']==split and m['label']==label]) for label in (1,0)} for split in ('dev','test')}
            require(all(len(ids)==42 for g in groups.values() for ids in g.values()),'42/42 dev and test per state')
            means=np.stack([np.stack([joined[k][1] for k in groups['dev'][label]]).mean(0,dtype=np.float64) for label in (1,0)])
            mu=means.mean(0);ids=sorted(groups['test'][1]+groups['test'][0]);h=np.asarray([joined[k][1] for k in ids],float)
            d,u,fraction=directions(means,q,np.random.default_rng(np.random.SeedSequence([20261028,ri,0])))
            targets=np.random.default_rng(np.random.SeedSequence([20261028,ri,1])).permutation(np.array([1]*42+[-1]*42))
            opaque=np.random.default_rng(np.random.SeedSequence([20261028,ri,2]));cells=[]
            if ri<3:
                cells=[('A','baseline',0,h)]+[('A',name,alpha,injection(h,d,u[ui],targets,alpha)) for alpha in (1,2,4) for ui,name in enumerate(('J','nonJ','random'))]
            else:cells=[('B','none',None,h)]+[('B',name,None,ablation(h,mu,u[ui])) for ui,name in enumerate(('J','nonJ','random'))]
            cell_reports=[]
            for arm,condition,alpha,values in cells:
                saved=values.astype(np.float32);require(np.isfinite(saved).all(),'finite saved vectors')
                ratio=np.linalg.norm(saved.astype(float),axis=1)/np.linalg.norm(h,axis=1)
                require(np.isfinite(ratio).all(),'finite norm ratio')
                cell_reports.append(dict(condition=condition,alpha=alpha,n=84,norm_ratio_mean=float(ratio.mean()),norm_ratio_min=float(ratio.min()),norm_ratio_max=float(ratio.max()),above_1_5=int((ratio>1.5).sum()),per_item=ratio.tolist()))
                for i,ident in enumerate(ids):
                    oid=opaque.bytes(16).hex();index=len(vectors);vectors.append(saved[i]);public.append(dict(id=oid,index=index,row=row,arm=arm,condition=condition,alpha=alpha,block=44))
                    private.append(dict(id=oid,source_item_id=ident,row=row,arm=arm,condition=condition,alpha=alpha,true_label=joined[ident][0]['label'],target_label=int(targets[i]>0) if arm=='A' else None,sign=int(targets[i]) if arm=='A' else None))
            cpu[row+'__means']=means;cpu[row+'__mu']=mu;cpu[row+'__d']=d;cpu[row+'__unit_directions']=u
            reports.append(dict(row=row,arm='A' if ri<3 else 'B',J_fraction=fraction,d_norm=float(np.linalg.norm(d)),cells=cell_reports))
        require(len(vectors)==3192 and len({x['id'] for x in public})==3192,'complete unique 3192-vector grid')
        np.save(pod/'INPUT_VECTORS.npy',np.asarray(vectors,np.float32),allow_pickle=False);write(pod/'ITEMS.json',public)
        write(out/'KEY.DO_NOT_SHARE.json',private);(out/'KEY.DO_NOT_SHARE.json').chmod(0o600)
        np.savez(out/'CPU_DIRECTIONS.npz',**cpu);(out/'CPU_DIRECTIONS.npz').chmod(0o600)
        seal_output(pod,dict(experiment='E79',status='SEALED_INPUTS_NO_READERS',n=3192,layer=44,input_spec_sha256=sha(plan)))
        write(HERE/'DIAGNOSTICS.json',dict(authority=s['authority'],basis_orthogonality_max_error=error,rows=reports,exclusions_applied=False))
        write(HERE/'BUILD_RECEIPT.json',dict(status='READY',n_vectors=3192,n_cells=38,pod_seal_sha256=sha(pod/'RESULT_SEAL.json'),private_map_sha256=sha(out/'KEY.DO_NOT_SHARE.json'),cpu_directions_sha256=sha(out/'CPU_DIRECTIONS.npz'),input_spec_sha256=sha(plan),wall_seconds=time.monotonic()-start,gpu_hours=0,reader_calls=0))
        seal_output(HERE,dict(experiment='E79',status='READY_SEALED_BEFORE_READERS',pod_seal_sha256=sha(pod/'RESULT_SEAL.json')))
    except Exception as e:
        write(out/'FAILED.json',dict(error_type=type(e).__name__,retry=False));raise


if __name__=='__main__':run()
