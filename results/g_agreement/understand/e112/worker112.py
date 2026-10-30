"""E112: supplied vectors only, one new PCA-1 condition, unchanged native adapters."""
import argparse
import os
import signal
import sys
import threading
import time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'late198'))
from contract import read,write,sha,verify,seal,require,deadline,digest,check_release
from runtime import Runtime
from worker import Clock,NoFit
CONDITIONS=('PCA1_ablated',)
CAPTURE_SHA='25d02e881f2c5ceb99959a6d6c8a0a640bf1daed4e1ba71491dd0f4b34e09a32'

def validate(inp,plan,items):
    require(plan['experiment']=='E112' and plan['conditions']==list(CONDITIONS),'all one new PCA-1 condition')
    require(plan['capture_seal_sha256']==CAPTURE_SHA and digest(plan['vector_seal_sha256']),'pinned capture and owner vectors')
    require(len(items)==518 and len({x['id'] for x in items})==518 and all(set(x)=={'id','feature'} for x in items),'518 public item identities')
    require(plan['item_ids']==[x['id'] for x in items],'owner vector order')
    values={}
    for l in (42,44):
        for condition in CONDITIONS:
            h=np.load(inp/f'{condition}{l}.npy',allow_pickle=False,mmap_mode='r')
            require(h.shape==(518,5120) and h.dtype==np.float32 and np.isfinite(h).all(),'unaltered finite owner float32 vectors')
            values[l,condition]=h
    return values

def acquire(items,vectors,b,c,out):
    count=65
    c.remaining=dict(oracle_setup=1,nla_setup=1,oracle_native=count,nla_native=count)
    jobs=out/'jobs';jobs.mkdir();totals={}
    for reader,layer in (('oracle',44),('nla',42)):
        c.call(reader+'_setup',b.load_oracle if reader=='oracle' else b.load_nla);c.remaining[reader+'_setup']=0
        dummy=np.random.default_rng(20261028).standard_normal((8,5120)).astype(np.float32)
        c.call(reader+'_warmup_discarded',lambda:b.native(reader,dummy))
        n=0
        for condition in CONDITIONS:
            h=vectors[layer,condition]
            for start in range(0,518,8):
                part=h[start:start+8].copy();before=part.tobytes()
                groups=c.call(reader+'_native',lambda:b.native(reader,part),real=True)
                require(part.tobytes()==before and len(groups)==len(part) and all(len(g)==1 for g in groups),'unchanged vectors, one greedy output')
                records=[dict(id=x['id']+':'+condition+':'+reader,unit_id=x['id'],feature=x['feature'],
                    condition=condition,reader=reader,layer=layer,repeat=0,**g[0]) for x,g in zip(items[start:start+8],groups)]
                write(jobs/f'{reader}_{condition}_{start//8:04d}.json',records)
                n+=len(records);c.remaining[reader+'_native']-=1;c.admit()
        totals[reader]=n;seal(jobs,reader+'_STAGE_SEAL.json',experiment='E112',reader=reader,status='COMPLETE')
    require(totals==dict(oracle=518,nla=518),'1x518x2 outputs; none is reused, never regenerated')
    write(out/'COUNTS.json',dict(new_readouts=1036,none_new_readouts=0,**totals))
    rows={}
    for p in jobs.glob('nla_*.json'):
        if p.name.endswith('SEAL.json'):continue
        for x in read(p):
            r=rows.setdefault(x['feature']+':'+x['condition'],dict(n=0,truncated=0));r['n']+=1;r['truncated']+=int('</explanation>' not in x['raw'])
    for r in rows.values():r['rate']=r['truncated']/r['n']
    write(out/'NLA_TRUNCATION.json',rows)

def main():
    p=argparse.ArgumentParser()
    for k in ('inputs','assets','assignment','out','go'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
    p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    verify(HERE,'SOURCE_SEAL.json',a.source_sha)
    for name,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==h,'source dependency')
    s=verify(a.inputs,'INPUT_SEAL.json',a.input_sha)
    expected={'PLAN.json','items.json','STAGE_REQUEST.json'}|{f'{c}{l}.npy' for c in CONDITIONS for l in (42,44)}
    require(set(s['files'])==expected and {str(p.relative_to(a.inputs)) for p in a.inputs.rglob('*') if p.is_file()}==expected|{'INPUT_SEAL.json'},'public-only vector archive')
    require(not s.get('synthetic',False) or a.dry_run,'synthetic fixtures not production')
    plan=read(a.inputs/'PLAN.json');items=read(a.inputs/'items.json');vectors=validate(a.inputs,plan,items)
    limits=read(a.inputs/'STAGE_REQUEST.json');ass=read(a.assignment)
    require(limits['status']=='READY' or a.dry_run,'sealed READY request required')
    end=deadline(ass,limits,time.time());read(a.assets);a.out.mkdir(parents=True,exist_ok=False)
    write(a.out/'ASSIGNMENT.json',ass)
    ready=dict(experiment='E112',pod_id=ass['pod_id'],source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,
        stage_seal_sha256=plan['vector_seal_sha256'],ready_epoch=time.time())
    write(a.out/'VECTORS_READY.json',ready)
    if a.dry_run:
        from test_worker112 import Tiny80c
        b=Tiny80c()
    else:b=Runtime(a.assets)
    c=Clock(a.out,end,limits['seed_seconds_per_batch'],b);status='COMPLETE'
    timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    try:
        if not a.dry_run:
            while not a.go.exists():c.check();time.sleep(1)
            go=read(a.go)
            ids=check_release(go,ready,[x['id'] for x in items],time.time(),forecast_required=True)
            require(ids==[x['id'] for x in items],'full518 release, no outcome selection')
            write(a.out/'GO_RECEIPT.json',go)
        acquire(items,vectors,b,c,a.out)
    except NoFit as e:status='NO_FIT';write(a.out/'NO_FIT.json',dict(reason=str(e),retained_pilots=True))
    except BaseException as e:write(a.out/'FAILURE.json',dict(reason=str(e)));raise
    finally:timer.cancel()
    if a.dry_run:write(a.out/'DRY_RUN.json',dict(status=status,GPU_calls=0))
    seal(a.out,'OUTPUT_SEAL.json',experiment='E112',status=status,synthetic=a.dry_run,
        source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,pod_id=ass['pod_id'],
        capture_seal_sha256=CAPTURE_SHA,vector_seal_sha256=plan['vector_seal_sha256'],recapture=False,none_regenerated=False)

if __name__=='__main__':main()
