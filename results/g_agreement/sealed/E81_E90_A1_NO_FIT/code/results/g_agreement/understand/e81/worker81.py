"""E81 two text instructions + E90 plain continuation; frozen opaque public prompts."""
import argparse
import os
from pathlib import Path
import signal
import sys
import threading
import time
from collections import Counter
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'late198'))
from contract import read,write,sha,verify,seal,require,deadline
from runtime import Runtime
from worker import Clock,NoFit

def validate(items):
    require(len(items)==11064 and len({x['id'] for x in items})==11064,'frozen11064 E81+E90 prompts')
    for x in items:
        require(set(x)=={'id','input_ids','prompt','read_position','max_new_tokens'},'only owner-public fields')
        require(x['input_ids'] and all(type(i)is int and i>=0 for i in x['input_ids']),'input tokens')
        require(x['read_position']==len(x['input_ids'])-1,'final frozen prompt token')
    require(Counter(x['max_new_tokens'] for x in items)=={128:7376,32:3688},'two128-token arms plus one32-token plain arm')
    return items

def jobs(items,batch_size):
    # Exact-length buckets avoid padding through Qwen's recurrent layers.
    buckets={}
    for x in items:buckets.setdefault((x['max_new_tokens'],len(x['input_ids'])),[]).append(x)
    return [(limit,xs[i:i+batch_size]) for (limit,length),xs in sorted(buckets.items(),reverse=True)
            for i in range(0,len(xs),batch_size)]

def acquire(items,b,c,out,limits):
    work=jobs(items,limits['batch_size'])
    c.remaining=dict(base_setup=1,base_text128=sum(n==128 for n,_ in work),base_text32=sum(n==32 for n,_ in work))
    c.call('base_setup',b.load_base);c.remaining['base_setup']=0
    b.check_tokens([dict(text=x['prompt'],ids=x['input_ids']) for x in items])
    stage=out/'jobs';stage.mkdir();warmed=set();seen=set()
    for number,(limit,chunk) in enumerate(work):
        phase='base_text'+str(limit)
        if limit not in warmed:
            dummy=b.synthetic()
            # Match configured batch size without reading any real prompt.
            dummy=[dummy[0] for _ in range(limits['batch_size'])]
            c.call(phase+'_warmup_discarded',lambda:b.text(dummy,max_new_tokens=limit));warmed.add(limit)
        result=c.call(phase,lambda:b.text([x['input_ids'] for x in chunk],max_new_tokens=limit),real=True)
        require(len(result)==len(chunk),'one greedy output per opaque prompt')
        rows=[dict(id=x['id'],text=r['raw'],token_ids=r['token_ids'],max_new_tokens=limit, **{k:limits[k] for k in ('run_id','code_sha256','run_kind') if k in limits}) for x,r in zip(chunk,result)]
        require(not seen.intersection(x['id'] for x in rows),'no duplicates');seen.update(x['id'] for x in rows)
        write(stage/f'{number:05d}.json',rows);c.remaining[phase]-=1;c.admit()
    require(seen=={x['id'] for x in items},'all three arms complete')
    write(out/'COUNTS.json',dict(prompts=len(seen),description_outputs=7376,plain_continuations=3688,reader_adapter_loads=0))

def main():
    p=argparse.ArgumentParser()
    for k in ('inputs','assets','assignment','out'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
    p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    verify(HERE,'SOURCE_SEAL.json',a.source_sha)
    for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'source dependency')
    s=verify(a.inputs,'INPUT_SEAL.json',a.input_sha)
    expected={'PUBLIC_INPUTS.json','STAGE_REQUEST.json'}
    require(set(s['files'])==expected and {x.name for x in a.inputs.iterdir()}==expected|{'INPUT_SEAL.json'},'no private mapping on pod')
    items=validate(read(a.inputs/'PUBLIC_INPUTS.json'));limits=read(a.inputs/'STAGE_REQUEST.json');ass=read(a.assignment)
    require(limits['status']=='READY' or a.dry_run,'READY request required')
    require(type(limits['batch_size'])is int and 1<=limits['batch_size']<=64,'bounded batch size')
    end=deadline(ass,limits,time.time());read(a.assets);a.out.mkdir(parents=True,exist_ok=False)
    write(a.out/'ASSIGNMENT.json',ass)
    if a.dry_run:
        from test_worker81 import Tiny81
        b=Tiny81()
    else:b=Runtime(a.assets)
    limits.update(run_id=ass['run_id'],code_sha256=sha(__file__),run_kind='synthetic' if a.dry_run else 'real')
    c=Clock(a.out,end,limits['seed_seconds_per_batch'],b);status='COMPLETE'
    timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    try:acquire(items,b,c,a.out,limits)
    except NoFit as e:status='NO_FIT';write(a.out/'NO_FIT.json',dict(reason=str(e),retained_pilots=True))
    except BaseException as e:write(a.out/'FAILURE.json',dict(reason=str(e)));raise
    finally:timer.cancel()
    if a.dry_run:write(a.out/'DRY_RUN.json',dict(status=status,GPU_calls=0))
    seal(a.out,'OUTPUT_SEAL.json',experiment='E81',includes='E90',status=status,synthetic=a.dry_run,
         source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,pod_id=ass['pod_id'])

if __name__=='__main__':main()
