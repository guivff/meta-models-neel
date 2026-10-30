"""E87 full-position capture, exact Gaussian placebo, trained-layer native sweep."""
import argparse
import os
from pathlib import Path
import signal
import sys
import threading
import time
import numpy as np

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'late198'))
from contract import read,write,sha,seal,verify,require,deadline
from worker import Clock,NoFit
from runtime import Runtime
LAYERS=(20,28,36,44,52,56,60)
CAPTURE_LAYERS=(20,28,36,42,44,52,56,60)
SEED=20261029
DIM=5120

def first_output(out):
    from scope99 import output_provenance
    return output_provenance(out)

def validate(items,plan):
    if plan['experiment']=='E95':
        from scope95 import validate95
        return validate95(items,plan,LAYERS,SEED)
    require(plan['experiment']=='E87' and plan['layers']==list(LAYERS) and plan['oracle_positions']==16
            and plan['nla_positions']==8 and plan['seed']==SEED,'registered sweep')
    require(len(items)==30*len(plan['row_indices']) and len({x['id'] for x in items})==len(items),'whole rows of30')
    require(set(plan['row_indices'])<=set(range(10)),'ten registered rows')
    require([x['global_index'] for x in items]==[r*30+i for r in plan['row_indices'] for i in range(30)],'frozen global order')
    require(plan['item_ids']==[x['id'] for x in items],'item order')
    for x in items:
        require(set(x)=={'id','global_index','ids','read_index','reuse44'},'public input allowlist')
        require(x['ids'] and all(type(t)is int and t>=0 for t in x['ids']),'token IDs')
        require(type(x['read_index'])is int and x['read_index']==len(x['ids'])-1 and x['read_index']>=0,'available positions exist')
        require(type(x['reuse44'])is bool,'reuse flag')
    return items

def norm_match(vectors,target):
    # Byte-for-byte arithmetic of W-text e76/common76.py:norm_match, pinned by NORM_RECIPE.json.
    x=np.asarray(vectors,dtype=np.float32);target=np.asarray(target,dtype=np.float64)
    norms=np.linalg.norm(x.astype(np.float64),axis=1)
    require(x.ndim==2 and x.shape[1]==DIM and target.shape==(len(x),) and np.isfinite(x).all()
        and np.isfinite(target).all() and (target>0).all() and (norms>0).all(),'Finite nonzero norm references required')
    out=(x.astype(np.float64)*(target/norms)[:,None]).astype(np.float32)
    require(np.allclose(np.linalg.norm(out.astype(np.float64),axis=1),target,rtol=1e-6,atol=0),'Norm scaling numerical failure')
    return out

def placebo(real,items,destination):
    """Global RNG order is independent of the pod/shard partition."""
    n=len(items);index={x['global_index']:i for i,x in enumerate(items)}
    medians={}
    for row in sorted({x['global_index']//30 for x in items}):
        ix=[i for i,x in enumerate(items) if x['global_index']//30==row]
        medians[row]={}
        for l in LAYERS:
            norms=np.linalg.norm(real[l][ix].astype(np.float64),axis=-1)
            medians[row][l]=np.array([np.median(norms[norms[:,j]>0,j]) if np.any(norms[:,j]>0) else 1.0 for j in range(16)])
    result={l:np.lib.format.open_memmap(destination/f'placebo{l}.npy',mode='w+',dtype=np.float32,shape=(n,16,DIM)) for l in LAYERS}
    rng=np.random.default_rng(SEED)
    for global_index in range(max(index)+1):
        z=rng.standard_normal((len(LAYERS),16,DIM)).astype(np.float32)
        if global_index not in index:continue
        i=index[global_index];row=global_index//30
        for k,l in enumerate(LAYERS):
            result[l][i]=0
            start=max(0,16-len(items[i]['ids']))
            result[l][i,start:]=norm_match(z[k,start:],medians[row][l][start:])
    for h in result.values():h.flush()
    write(destination/'NORM_MATCH.json',dict(seed=SEED,order='global row,item,layer,position,coordinate',
        target='median of30 real norms at same row/layer/position',
        row_layer_position_medians={str(r):{str(l):v.tolist() for l,v in d.items()} for r,d in medians.items()},
        adapter_changes=False))
    return result

class Backend87(Runtime):
    def confirm_layers(self):
        from mats.readers.olens import TRAINED_LAYERS
        require(set(LAYERS)<=set(TRAINED_LAYERS),'all Oracle layers must be trained')
        return list(TRAINED_LAYERS)

    def capture_all(self,item,layers):
        import torch
        from mats.capture import capture
        model,tok,cm=self.subject()
        with cm,torch.inference_mode():
            values=capture(model,[item['ids']],layers,[list(range(len(item['ids'])))],batch_size=1,pad_id=tok.pad_token_id or 0)
        return {l:v[0].float().cpu().numpy() for l,v in values.items()}

    def warm_capture(self):
        ids=self.synthetic()[0]
        self.capture_all(dict(ids=ids),CAPTURE_LAYERS)

    def sweep(self,reader,vectors,layer):
        import torch
        if reader=='nla':
            from native_nla512 import native_nla
            require(layer==42,'NLA only block42')
            return [x[0] for x in native_nla(self.readers.nla,vectors,k=1,batch=getattr(self,'sweep_batch_size',8))]
        from mats.readers.nla import Sampling
        with torch.inference_mode():
            groups=self.readers.oracle.verbalize(torch.as_tensor(np.array(vectors,copy=True)),layer,k=1,
                sampling=Sampling(temperature=0,top_p=1.,top_k=0,max_new_tokens=128),batch=getattr(self,'sweep_batch_size',8))
        require(all(len(g)==1 for g in groups),'one greedy Oracle per cell')
        return [dict(raw=g[0],text=g[0],malformed=False,native_max_new_tokens=128) for g in groups]

def capture_stage(inp,items,b,c,out,binding,plan=None):
    cap=out/'capture';cap.mkdir();full=cap/'full';full.mkdir()
    capture_layers=tuple(sorted(set(plan['layers'])|{42})) if plan and plan['experiment']=='E95' else CAPTURE_LAYERS
    arrays={l:np.lib.format.open_memmap(cap/f'grid{l}.npy',mode='w+',dtype=np.float32,shape=(len(items),16,DIM)) for l in capture_layers}
    positions=[]
    c.call('capture_warmup_discarded',b.warm_capture)
    for i,item in enumerate(items):
        layers=tuple(l for l in capture_layers if l!=44 or not item['reuse44'])
        values=c.call('capture',lambda:b.capture_all(item,layers),real=True)
        if item['reuse44']:
            values[44]=np.load(inp/'reuse44'/f"{item['id']}.npy",allow_pickle=False)
        folder=full/item['id'];folder.mkdir()
        for l in capture_layers:
            h=values[l]
            require(h.shape==(len(item['ids']),DIM) and np.isfinite(h).all(),'full-position capture shape')
            np.save(folder/f'{l}.npy',h.astype(np.float16))
            arrays[l][i]=0
            take=min(16,len(h));arrays[l][i,-take:]=h[-take:]
        positions.append(dict(id=item['id'],global_index=item['global_index'],prompt_positions=len(item['ids']),
            oracle_positions=list(range(max(0,item['read_index']-(plan['oracle_positions'] if plan else 16)+1),item['read_index']+1)),
            nla_positions=list(range(max(0,item['read_index']-7),item['read_index']+1)),reused_layers=[44] if item['reuse44'] else []))
        c.remaining['capture']-=1
        # Forecast is recorded after pilots, but full-scope cap never changes.
        c.admit()
    for h in arrays.values():h.flush()
    write(cap/'POSITIONS.json',positions)
    if plan and plan['experiment']=='E95':
        from scope95 import placebo95
        p=c.call('placebo_build',lambda:placebo95(arrays,items,plan,cap,tuple(plan['layers']),DIM,norm_match))
    else:
        p=c.call('placebo_build',lambda:placebo(arrays,items,cap))
    c.remaining['placebo_build']=0
    digest_value=seal(cap,'CAPTURE_SEAL.json',**binding,layers=list(capture_layers),reader_outputs=0,first_output_utc='unknown',first_output_evidence=None)
    write(out/'CAPTURE_READY.json',dict(binding,capture_seal_sha256=digest_value,reader_outputs=0,ready_epoch=time.time()))
    return arrays,p

def acquire(inp,items,plan,b,c,out,binding):
    if plan['experiment']=='E95' and plan['mode']=='nla_placebo_only':
        from scope95 import acquire_reuse_placebo
        return acquire_reuse_placebo(items,plan,b,c,out,binding,LAYERS,DIM,norm_match)
    n=len(items)
    extended=plan['experiment']=='E95'
    oracle_layers=tuple(plan['layers']) if extended else LAYERS
    if extended:
        from scope95 import pseudo_items
        pseudos=pseudo_items(plan)
    else:pseudos=items
    npseudo=len(pseudos);nla_placebo=extended and plan['nla_placebo']
    def offsets(item,reader):
        width=plan['oracle_positions'] if reader=='oracle' else 8
        count=min(width,len(item['ids'])) if 'ids' in item else min(width,item.get('position_count',width))
        return list(range(16-count,16))
    oracle_count=sum(len(offsets(x,'oracle')) for x in items+pseudos)*len(oracle_layers)
    nla_count=sum(len(offsets(x,'nla')) for x in items+(pseudos if nla_placebo else []))
    oracle_batches=sum((len(offsets(x,'oracle'))+7)//8 for x in items+pseudos)*len(oracle_layers)
    c.remaining=dict(oracle_setup=1,capture=n,placebo_build=1,oracle_native=oracle_batches,nla_setup=1,nla_native=n+(npseudo if nla_placebo else 0))
    c.call('oracle_setup',b.load_oracle);c.remaining['oracle_setup']=0
    write(out/'TRAINED_LAYERS.json',dict(requested=list(oracle_layers),trained=b.confirm_layers(),status='PASS'))
    real,random=capture_stage(inp,items,b,c,out,binding,plan)
    jobs=out/'jobs';jobs.mkdir();counts={'oracle':0,'nla':0}
    for reader,layers in [('oracle',oracle_layers),('nla',(42,))]:
        if reader=='nla':c.call('nla_setup',b.load_nla);c.remaining['nla_setup']=0
        for layer in layers:
            dummy=np.random.default_rng(SEED+layer).standard_normal((8,DIM)).astype(np.float32)
            c.call(f'{reader}_{layer}_warmup_discarded',lambda:b.sweep(reader,dummy,layer))
            for arm in (('real','placebo') if reader=='oracle' or nla_placebo else ('real',)):
                matrix=(real if arm=='real' else random)[layer]
                for i,item in enumerate(items if arm=='real' else pseudos):
                    positions=offsets(item,reader)
                    for offset in range(0,len(positions),8):
                        ix=positions[offset:offset+8]
                        if getattr(c,'profile95',False) and not c.select(reader,arm,layer,len(ix)):continue
                        h=matrix[i,ix].copy();before=h.tobytes()
                        values=(c.native(reader,arm,layer,h,lambda:b.sweep(reader,h,layer)) if getattr(c,'profile95',False)
                            else c.call(reader+'_native',lambda:b.sweep(reader,h,layer),real=True))
                        require(h.tobytes()==before and len(values)==len(ix),'native grid unchanged')
                        records=[dict(id=f"{item['id']}:{reader}:{arm}:{layer}:{j}",unit_id=item['id'],
                            global_index=item['global_index'],reader=reader,arm=arm,layer=layer,
                            position=item['read_index']-15+j,position_offset=j-15,**v) for j,v in zip(ix,values)]
                        write(jobs/f'{reader}_{arm}_{layer}_{i:03d}_{offset:02d}.json',records)
                        counts[reader]+=len(records);c.remaining[reader+'_native']-=1;c.admit()
        seal(jobs,reader+'_STAGE_SEAL.json',**binding,reader=reader,status='COMPLETE',**first_output(out))
    if not getattr(c,'profile95',False):require(counts=={'oracle':oracle_count,'nla':nla_count},'entire registered grid')
    write(out/'COUNTS.json',counts)
    rows={}
    for path in sorted(jobs.glob('nla_*.json')):
        if path.name.endswith('SEAL.json'):continue
        for x in read(path):
            r=rows.setdefault(str(x['global_index']//(15 if extended and x['arm']=='placebo' else 30)),dict(n=0,truncated=0));r['n']+=1;r['truncated']+=int('</explanation>' not in x['raw'])
    for r in rows.values():r['rate']=r['truncated']/r['n']
    write(out/'NLA_TRUNCATION.json',rows)

def main():
    if '--stage99' in sys.argv:
        from scope99 import main as main99
        return main99()
    p=argparse.ArgumentParser()
    for k in ('inputs','assets','assignment','out'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
    p.add_argument('--hardware-receipt',type=Path);p.add_argument('--reuse-hardware',type=Path)
    p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    verify(HERE,'SOURCE_SEAL.json',a.source_sha)
    for name,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==h,'dependency')
    s=verify(a.inputs,'INPUT_SEAL.json',a.input_sha);plan=read(a.inputs/'PLAN.json');items=validate(read(a.inputs/'items.json'),plan)
    expected={'PLAN.json','items.json','STAGE_REQUEST.json'}|{f"reuse44/{x['id']}.npy" for x in items if x['reuse44']}
    require(set(s['files'])==expected and {str(f.relative_to(a.inputs)) for f in a.inputs.rglob('*') if f.is_file()}==expected|{'INPUT_SEAL.json'},'strict public-only archive')
    require(not s.get('synthetic',False) or a.dry_run,'synthetic inputs forbidden for production')
    limits=read(a.inputs/'STAGE_REQUEST.json');ass=read(a.assignment)
    require(limits['status']=='READY' or a.dry_run,'request must be READY')
    require(ass['shard']==plan['shard'] and ass['row_indices']==plan['row_indices'],'shard binding')
    from hardware204 import bind_units,production_gate
    reused=None
    if plan['experiment']=='E95' and plan['mode']=='nla_placebo_only':
        require(a.reuse_hardware and sha(a.reuse_hardware)==ass['reuse_hardware_sha256'],'original E87 hardware receipt')
        reused=read(a.reuse_hardware)
    bind_units(ass,plan['row_indices'],reused)
    hardware=dict(gpu_type=ass['gpu_type'],synthetic=True) if a.dry_run else production_gate(ass,a.hardware_receipt,a.assets,['oracle','nla'])
    if plan['experiment']=='E95' and not a.dry_run:
        from timing95 import validate_production
        validate_production(ass,limits,plan,a.inputs,a.source_sha)
        require(ass['assets_sha256']==sha(a.assets),'production asset identity')
        from hardware204 import validate_e95
        hardware['e95_policy']=validate_e95(ass,plan,reused,a.hardware_receipt,hardware)
    end=deadline(ass,limits,time.time());read(a.assets)
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass)
    if a.dry_run:
        from test_worker87 import Tiny87
        b=Tiny87()
    else:
        b=Backend87(a.assets);b.hardware_assignment=ass
    c=Clock(a.out,end,limits['seed_seconds_per_batch'],b)
    binding=dict(experiment=plan['experiment'],pod_id=ass['pod_id'],shard=plan['shard'],source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,synthetic=a.dry_run,gpu_type=ass['gpu_type'],hardware=hardware)
    timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='COMPLETE'
    try:acquire(a.inputs,items,plan,b,c,a.out,binding)
    except NoFit as error:
        status='NO_FIT';write(a.out/'NO_FIT.json',dict(reason=str(error),retained_pilots=True))
    except BaseException as error:
        write(a.out/'FAILURE.json',dict(reason=str(error),type=type(error).__name__));raise
    finally:timer.cancel()
    if a.dry_run:write(a.out/'DRY_RUN.json',dict(status=status,GPU_calls=0))
    seal(a.out,'OUTPUT_SEAL.json',**binding,status=status,**first_output(a.out))

if __name__=='__main__':main()
