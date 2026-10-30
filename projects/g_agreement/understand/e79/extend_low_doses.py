"""Append registered low-dose E79 cells; preserve original inputs and private map."""
import subprocess,time
from pathlib import Path
import numpy as np
from .build import ROOT,ROWS,injection
from projects.g_agreement.readerbench.io import read,write,sha,verify,seal_output
from projects.g_agreement.readerbench.scoring import require
HERE=ROOT/'results/g_agreement/understand/e79/clarification2'


def new_cells(h,d,u,signs):
    return [(alpha,name,injection(h,d,u[i],signs,alpha).astype(np.float32))
            for alpha in (.25,.5) for i,name in enumerate(('J','nonJ','random'))]


def run():
    start=time.monotonic();plan=HERE/'INPUTS.json';spec=read(plan)
    require(subprocess.check_output(['git','show','HEAD:'+str(plan.relative_to(ROOT))],cwd=ROOT)==plan.read_bytes(),'commit extension freeze first')
    for f,digest in spec['files'].items():require(sha(f)==digest,'frozen extension input')
    for f,digest in spec['seals'].items():verify(f,digest)
    original=Path(spec['original']);oldpod=original/'pod_inputs'
    old=np.load(oldpod/'INPUT_VECTORS.npy',allow_pickle=False);pub=read(oldpod/'ITEMS.json');key=read(original/'KEY.DO_NOT_SHARE.json')
    cpu=np.load(original/'CPU_DIRECTIONS.npz',allow_pickle=False)
    require(old.shape==(3192,5120) and len(pub)==len(key)==3192,'complete original grid')
    require([x['id'] for x in pub]==[x['id'] for x in key],'old private/public grid')
    out=Path(spec['output']);require(subprocess.run(['git','check-ignore','-q',str(out/'KEY.DO_NOT_SHARE.json')],cwd=ROOT).returncode==0,'private output ignored')
    out.mkdir(parents=True,exist_ok=False);out.chmod(0o700);pod=out/'pod_inputs';pod.mkdir()
    vectors=[old];public=list(pub);private=list(key);reports=[];next_index=len(old)
    try:
        for ri,row in enumerate(ROWS[:3]):
            baseline=[(p,k) for p,k in zip(pub,key) if p['row']==row and p['arm']=='A' and p['alpha']==0]
            require(len(baseline)==84,'one shared baseline per source item')
            ids=[k['source_item_id'] for p,k in baseline];require(ids==sorted(ids) and len(set(ids))==84,'original item order')
            signs=np.array([k['sign'] for p,k in baseline]);require(sum(signs==1)==sum(signs==-1)==42,'unchanged balanced targets')
            require(all(k['target_label']==int(k['sign']>0) for p,k in baseline),'target/sign consistency')
            h=np.asarray([old[p['index']] for p,k in baseline],float)
            d=cpu[row+'__d'];u=cpu[row+'__unit_directions']
            # Continue original row stream2 after all840 original Arm A IDs.
            rng=np.random.default_rng(np.random.SeedSequence([20261028,ri,2]))
            generated=[rng.bytes(16).hex() for _ in range(840)]
            require(generated==[p['id'] for p in pub if p['row']==row],'same original opaque-ID stream')
            cells=[]
            for alpha,name,saved in new_cells(h,d,u,signs):
                require(saved.shape==(84,5120) and np.isfinite(saved).all(),'finite new vectors')
                ratios=np.linalg.norm(saved.astype(float),axis=1)/np.linalg.norm(h,axis=1)
                cells.append(dict(alpha=alpha,condition=name,n=84,norm_ratio_mean=float(ratios.mean()),norm_ratio_min=float(ratios.min()),norm_ratio_max=float(ratios.max()),above_1_5=int(sum(ratios>1.5)),per_item=ratios.tolist()))
                vectors.append(saved)
                for i,(p,k) in enumerate(baseline):
                    oid=rng.bytes(16).hex();public.append(dict(p,id=oid,index=next_index,alpha=alpha,condition=name))
                    private.append(dict(k,id=oid,alpha=alpha,condition=name));next_index+=1
            reports.append(dict(row=row,cells=cells))
        combined=np.concatenate(vectors,axis=0)
        require(combined.shape==(4704,5120) and len({p['id'] for p in public})==4704,'complete unique extended grid')
        require(np.array_equal(combined[:3192],old) and public[:3192]==pub and private[:3192]==key,'existing vectors/IDs/map unchanged')
        np.save(pod/'INPUT_VECTORS.npy',combined,allow_pickle=False);write(pod/'ITEMS.json',public)
        write(out/'KEY.DO_NOT_SHARE.json',private);(out/'KEY.DO_NOT_SHARE.json').chmod(0o600)
        seal_output(pod,dict(experiment='E79',authority='1e879d02',status='SEALED_INPUTS_NO_READERS',n=4704,layer=44,original_pod_seal_sha256=spec['original_pod_seal_sha256'],input_spec_sha256=sha(plan)))
        write(HERE/'NORM_RATIOS.json',dict(rows=reports,added_vectors=1512,exclusions_applied=False))
        write(HERE/'BUILD_RECEIPT.json',dict(status='READY',n_vectors=4704,added_vectors=1512,n_cells=56,arm_A_cells_per_state=16,original_prefix_unchanged=True,original_private_map_unchanged=True,target_assignments_unchanged=True,pod_seal_sha256=sha(pod/'RESULT_SEAL.json'),private_map_sha256=sha(out/'KEY.DO_NOT_SHARE.json'),wall_seconds=time.monotonic()-start,reader_calls=0,gpu_hours=0))
        for f,digest in spec['files'].items():require(sha(f)==digest,'original input mutated')
        seal_output(HERE,dict(experiment='E79',authority='1e879d02',status='READY',pod_seal_sha256=sha(pod/'RESULT_SEAL.json')))
    except Exception as exc:
        write(out/'FAILED.json',dict(error_type=type(exc).__name__,retry=False));raise


if __name__=='__main__':run()
