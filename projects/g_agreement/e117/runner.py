"""Sealed precomposed E117 directions only; no labels/probe fitting on GPU."""
import argparse,math,os,signal,threading,time
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import ROOT,read,write,sha,verify,require
from projects.g_agreement.e100.worker import original,backend,hardware
from .hook import read as hooked_read
ROWS=('nesting_depth','indent_level','page_range_digit','fact_recall')

def load(root,input_sha):
    s=verify(root,'INPUT_SEAL.json',input_sha);m=read(root/'MANIFEST.json');items=read(root/'items.json')
    require(s['experiment']==m['experiment']=='E117' and s['labels_on_pod'] is False,'E117 public inputs')
    require(set(s['files'])=={'MANIFEST.json','items.json','H44.npy','DELTAS.npy'},'public-only exact input members')
    h=np.load(root/'H44.npy',allow_pickle=False);d=np.load(root/'DELTAS.npy',allow_pickle=False)
    require(h.shape==(336,5120) and d.shape==(336,3,5120) and h.dtype==d.dtype==np.float32 and np.isfinite(h).all() and np.isfinite(d).all(),'native carriers and signed gap-scaled T/W/R vectors')
    require(len(items)==336 and len({x['id'] for x in items})==336,'original336 unique test items')
    require(m['direction_source']=='E113 sealed dev fits; no refit' and m['alphas']==[1,2,4] and m['arms']==['T','W','R'],'frozen intervention')
    require(set(m['rows'])==set(ROWS),'four registered rows')
    for row in ROWS:
        require(sum(x['row']==row for x in items)==84 and 48<=m['rows'][row]['lens_layer']<=60,'whole row and dev-selected lens layer')
        require(m['rows'][row]['gap']>0 and bool(m['rows'][row]['selection_seal_sha256']),'frozen dev gap/selection binding')
    require(all(set(x)=={'id','row','slot'} and type(x['slot']) is int for x in items),'opaque item allowlist')
    for row in ROWS:
        positions=[i for i,x in enumerate(items) if x['row']==row];slots=[items[i]['slot'] for i in positions]
        require(slots==positions or slots==list(range(84)),'frozen global or row-local item slots; arrays use list order')
    require(np.allclose(d[:,0],-d[:,1],rtol=1e-5,atol=1e-6),'true/wrong opposite')
    norms=np.linalg.norm(d.astype(float),axis=-1)
    require(np.all(norms>0) and np.allclose(norms,norms[:,:1],rtol=2e-5),'matched norm random control')
    for i,x in enumerate(items):require(np.isclose(norms[i,0],m['rows'][x['row']]['gap'],rtol=2e-5),'gap-scaled unit directions')
    return items,h,d,m

def whole_grid_forecast(total_calls,completed_calls,observed_seconds,custody_start,deadline,now):
    require(0<=completed_calls<=total_calls and now>=custody_start,'original custody and complete call census')
    require(bool(observed_seconds) and all(math.isfinite(v) and v>0 for v in observed_seconds),'measured retained read calls required')
    worst=max(observed_seconds);pending=total_calls-completed_calls;elapsed=now-custody_start
    remaining=pending*worst
    cap=1.25*(elapsed+remaining)+60
    status='COMPLETE' if pending==0 and now<deadline-60 else ('ADMIT' if custody_start+cap<=deadline else 'NO_FIT')
    return dict(status=status,total_calls=total_calls,completed_calls=completed_calls,
        pending_calls=pending,max_observed_call_seconds=worst,remaining_work_bound_seconds=remaining,
        elapsed_custody_including_staging_setup_warmup_and_completed_work=elapsed,
        projected_total_cap_seconds=cap,margin=1.25,reserve_seconds=60,
        absolute_deadline_epoch=deadline,custody_start_epoch=custody_start,
        unseen_rows_and_final_batches='every pending call charged global worst observed call, no omitted/unmeasured strata',pilots_retained=True)

def acquire(items,h,d,m,b,clock,out,gpu,custody_start):
    clock.call('oracle_setup',b.load_oracle);lens=b.oracle
    first=items[0];layer=m['rows'][first['row']]['lens_layer']
    clock.call('warmup_discarded',lambda:hooked_read(lens,h[:1],np.zeros_like(h[:1]),layer))
    jobs=[dict(row=row,alpha=a,arm=arm,indices=ix[k:k+8]) for row in ROWS for a in (1,2,4) for arm in range(3) for ix in [[i for i,x in enumerate(items) if x['row']==row]] for k in range(0,84,8)]
    write(out/'JOB_GRID.json',jobs);(out/'jobs').mkdir();observed=[];completed=[]
    for number,j in enumerate(jobs):
        ix=j['indices'];key=(j['row'],len(ix));phase='read:'+str(key);clock.cost.setdefault(phase,[])
        values=clock.call(phase,lambda:hooked_read(lens,h[ix],j['alpha']*d[ix,j['arm']],m['rows'][j['row']]['lens_layer']))
        observed.append(clock.cost[phase][-1]);write(out/'jobs'/f'{number:06d}.json',[dict(v,id=items[i]['id']+f":{j['arm']}:{j['alpha']}",item_id=items[i]['id'],row=j['row'],arm=('T','W','R')[j['arm']],alpha=j['alpha'],gpu_type=gpu) for i,v in zip(ix,values)])
        completed.append(number);write(out/'COMPLETED.json',completed)
        forecast=whole_grid_forecast(len(jobs),len(completed),observed,custody_start,clock.end,time.time())
        write(out/'FORECAST.json',forecast)
        if forecast['status']=='NO_FIT':return 'NO_FIT'
    return 'COMPLETE'

def main():
    p=argparse.ArgumentParser()
    for n in ('inputs','assignment','assets','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('source-sha','input-sha'):p.add_argument('--'+n,required=True)
    p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    verify(ROOT,str(a.source_seal.resolve().relative_to(ROOT)),a.source_sha);items,h,d,m=load(a.inputs,a.input_sha)
    if a.validate_only:return
    ass=read(a.assignment);require(ass['experiment']=='E117' and ass['source_sha256']==a.source_sha and ass['input_sha256']==a.input_sha and ass['assets_sha256']==sha(a.assets),'source/input/assets custody')
    require(ass['pod_id']==os.environ.get('RUNPOD_POD_ID') and ass['gpu_type']=='H200' and ass['allocation_verified'] is True and ass['daily_budget_verified'] is True,'operator GO')
    require(0<ass['cap_seconds'] and ass['cap_seconds']*5.29/3600<=25 and ass['pod_created_epoch']<1793296800 and ass['absolute_deadline_epoch']==ass['pod_created_epoch']+ass['cap_seconds'],'measured cap/19CET create deadline')
    actual=hardware(ass);a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);status='FAILED'
    timer=threading.Timer(max(0,ass['absolute_deadline_epoch']-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    try:status=acquire(items,h,d,m,backend(a.assets,ass),original().Clock(a.out,ass['absolute_deadline_epoch']),a.out,actual,ass['pod_created_epoch'])
    finally:
        timer.cancel();write(a.out/'OUTPUT_SEAL.json',dict(experiment='E117',status=status,source_sha256=a.source_sha,input_sha256=a.input_sha,gpu_type=actual,files={str(p.relative_to(a.out)):sha(p) for p in a.out.rglob('*') if p.is_file() and p.name!='OUTPUT_SEAL.json'}))
if __name__=='__main__':main()
