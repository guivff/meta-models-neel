"""E100 a native full transplant only; same-pod retained timing, no labels/judging."""
import argparse,json,math,os,signal,threading,time
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import ROOT,read,write,sha,verify,require
from projects.g_agreement.e100.worker import original,backend,hardware
from projects.g_agreement.e100.interventions import transform,ratios
from .build import ROWS,SEED

def load(root,input_sha,dimension=5120):
    s=verify(root,'INPUT_SEAL.json',input_sha);m=read(root/'MANIFEST.json');items=read(root/'items.json')
    require(s['experiment']==m['experiment']=='E100e' and s['labels_on_pod'] is m['labels_on_pod'] is False,'public E100e seals')
    require(m['seed']==SEED and m['condition']=='transplant' and m['rows']==list(ROWS) and m['test_per_row']==84 and m['read_blocks']=={'oracle':44,'nla':42},'frozen E100e scope')
    require(set(s['files'])=={'MANIFEST.json','items.json','H42.npy','H44.npy'},'only public members')
    arrays={b:np.load(root/f'H{b}.npy',allow_pickle=False) for b in (42,44)}
    validate(items,arrays,dimension);return items,arrays

def validate(items,arrays,dimension=5120):
    require(len(items)==168 and len({x['id'] for x in items})==168,'168 original distinct units')
    require([x['slot'] for x in items]==list(range(168)),'sealed global slots')
    for row in ROWS:
        xs=[x for x in items if x['row']==row];require(len(xs)==84 and [x['row_slot'] for x in xs]==list(range(84)),'84 test items per row in frozen order')
    for x in items:
        require(set(x)=={'id','row','slot','row_slot','donor_slot'},'opaque public allowlist')
        d=x['donor_slot'];require(type(d)is int and 0<=d<168 and d!=x['slot'] and items[d]['row']==x['row'],'same-row donor')
    require(set(arrays)=={42,44},'native 42/44 carriers only')
    for h in arrays.values():require(h.shape==(168,dimension) and h.dtype==np.float32 and np.isfinite(h).all() and np.all(np.linalg.norm(h,axis=1)>0),'finite nonzero native arrays')

def jobs(items):
    return [dict(reader=r,row=row,indices=ix[i:i+8],phase=r+':'+str(len(ix[i:i+8]))) for r in ('oracle','nla') for row in ROWS for ix in [[x['slot'] for x in items if x['row']==row]] for i in range(0,84,8)]

def cap_formula(profiles):
    require(bool(profiles),'measured own-experiment profiles required')
    for p in profiles:
        require(p['experiment']=='E100e' and p['measured'] is True and p['staging_seconds']>=0 and p['setup_warmup_seconds']>=0 and set(p['work_seconds'])=={'oracle','nla'} and all(v>0 for v in p['work_seconds'].values()),'actual measured E100e profiles, both readers')
    setup=max(p['staging_seconds']+p['setup_warmup_seconds'] for p in profiles)
    work=sum(max(p['work_seconds'][r] for p in profiles) for r in ('oracle','nla'))
    return setup+1.25*work+180

OPERATIONAL_NOTE='f599f121a2addd54fa2f1f2039bbe31d83e1267d'
DEFAULT_ATTEMPT_CAP=1800

def retry_limit(a,out):
    """Operator's sealed CPU timing summary; no previous output is a reader input."""
    require(a.get('operational_note_commit')==OPERATIONAL_NOTE and a.get('attempt')==2,'only authorized attempt2 can override the cap')
    profile=Path(a['attempt1_profile']);require(sha(profile)==a['attempt1_profile_sha256'],'attempt1 measured profile SHA')
    p=read(profile)
    require(p['experiment']=='E100e' and p['attempt']==1,'original attempt1 timing profile')
    root=Path(p['output_root']).resolve();seal=verify(root,'OUTPUT_SEAL.json',p['output_seal_sha256'])
    require(seal['experiment']=='E100e' and seal['status']=='NO_FIT','attempt1 terminal NO_FIT')
    require(seal.get('input_sha256')==a['input_seal_sha256'],'same frozen inputs across attempts')
    require('PHASE_TIMINGS.json' in seal['files'] and any(n.startswith('FORECAST_') and n.endswith('.json') for n in seal['files']),'sealed measured timing and forecast')
    timings=read(root/'PHASE_TIMINGS.json')
    require(any(x['phase'] in ('oracle_setup','nla_setup') and x['status']=='COMPLETE' for x in timings),'attempt1 NO_FIT occurred after load')
    require(out is not None,'override needs an explicit fresh attempt folder')
    dest=Path(out).resolve();require(not Path(out).exists() and dest!=root and not dest.is_relative_to(root) and not root.is_relative_to(dest),'fresh independent attempt folder, no previous outputs')
    require(math.isfinite(p['custody_seconds']) and p['custody_seconds']>0 and a['prior_seconds']==p['custody_seconds'],'retain actual attempt1 custody')
    parts=[p['staging_seconds'],p['setup_warmup_seconds'],*p['work_seconds'].values()]
    require(set(p['work_seconds'])=={'oracle','nla'} and all(math.isfinite(v) and v>=0 for v in parts) and all(v>0 for v in p['work_seconds'].values()),'full measured staging/setup/warmup/work need')
    return math.ceil(1.25*sum(parts)+60)

def fresh_attempt(out):
    # No resume path: even an existing empty directory or copied partial is refused.
    Path(out).mkdir(parents=True,exist_ok=False)

def assignment(a,input_sha,source_sha,assets_sha,attempt_cap_seconds=DEFAULT_ATTEMPT_CAP,out=None):
    require(a['experiment']=='E100e' and a['gpu_type']=='H200' and a['gpu_count']==1,'one H200, both full rows')
    require(a['input_seal_sha256']==input_sha and a['source_seal_sha256']==source_sha and a['assets_sha256']==assets_sha,'exact source/input/assets')
    require(math.isfinite(attempt_cap_seconds) and attempt_cap_seconds>0,'finite positive per-attempt cap')
    if attempt_cap_seconds==DEFAULT_ATTEMPT_CAP:
        require(a['prior_seconds']>=0 and 0<a['cap_seconds']<=1800-a['prior_seconds'] and a['authorized_cumulative_seconds']==1800,'registered half GPU-hour cumulative')
    else:
        limit=retry_limit(a,out)
        require(0<a['cap_seconds']<=attempt_cap_seconds<=limit,'attempt2 cap bounded by measured need times1.25 plus60')
        require(a['authorized_cumulative_seconds']==a['prior_seconds']+attempt_cap_seconds,'explicit cumulative custody includes original attempt')
        require(attempt_cap_seconds*5.29/3600<=25,'attempt2 H200 cost no more than25 USD')
    require(a['pod_created_epoch']==a['custody_start_epoch'] and a['absolute_deadline_epoch']==a['pod_created_epoch']+a['cap_seconds'],'creation custody clock')
    require(a['pod_id']==os.environ.get('RUNPOD_POD_ID') and a['allocation_verified'] is True and a['daily_budget_verified'] is True,'provider identity/budget admission')
    require(0<=a['projected_daily_USD']<=a['daily_budget_USD'],'daily budget')
    require(a['mode'] in ('timing','production'),'explicit timing or production')
    if a['mode']=='production' and attempt_cap_seconds==DEFAULT_ATTEMPT_CAP:require(a['cap_seconds']>=cap_formula(a['measured_profiles']),'production cap covers max setup, measured work times1.25,180s reserve')

def acquire(items,arrays,b,clock,out,gpu_type):
    jj=jobs(items);write(out/'JOB_GRID.json',jj);(out/'jobs').mkdir();done=[];clock.cost={j['phase']:[] for j in jj}
    for reader in ('oracle','nla'):
        clock.call(reader+'_setup',getattr(b,'load_'+reader))
        dummy=np.random.default_rng(SEED).standard_normal((8,arrays[44].shape[1])).astype(np.float32)
        clock.call(reader+'_warmup_discarded',lambda:b.native_one(reader,dummy))
        active=[i for i,j in enumerate(jj) if j['reader']==reader]
        def run(i):
            j=jj[i];xs=[items[k] for k in j['indices']];block=44 if reader=='oracle' else 42
            h=arrays[block][j['indices']].copy();donor=arrays[block][[x['donor_slot'] for x in xs]].copy();hp=transform(h,donor,'transplant');snapshot=hp.tobytes()
            values=clock.call(j['phase'],lambda:b.native_one(reader,hp))
            require(hp.tobytes()==snapshot and np.array_equal(h,arrays[block][j['indices']]) and len(values)==len(xs) and all(len(v)==1 for v in values),'one native readout, immutable input')
            rr=ratios(h,hp)
            records=[dict(id=x['id']+':'+reader+':transplant',item_id=x['id'],row=x['row'],reader=reader,condition='transplant',mode='transplant',repeat=0,read_block=block,inject_block=block,norm_ratio=float(r),norm_over_1_5=bool(r>1.5),read_layer_norm_ratio=float(r),gpu_type=gpu_type,**v[0]) for x,r,v in zip(xs,rr,values)]
            write(out/'jobs'/f'{i:06d}.json',records);done.append(i);write(out/'COMPLETED.json',done)
        # Retain one real pilot per reader and actual batch shape, never replay it.
        for phase in dict.fromkeys(jj[i]['phase'] for i in active):run(next(i for i in active if jj[i]['phase']==phase))
        for i in active:
            if i in done:continue
            remaining=[jj[k] for k in active if k not in done]
            seconds=1.25*sum(float(np.mean(clock.cost[j['phase']])) for j in remaining)
            fits=time.time()+seconds<clock.end-60
            write(out/('FORECAST_'+reader+'.json'),dict(status='ADMIT' if fits else 'NO_FIT',scope='current reader only; next setup charged to fixed custody',remaining_seconds=seconds,margin=1.25,pilots_retained=True,warmups_discarded=True))
            if not fits:return False
            run(i)
    require(len(done)==44,'complete336 readouts');return True

def main():
    if '--cpu-import-only' in __import__('sys').argv:
        original();from projects.g_agreement.blindspot import run
        require(callable(run._load_oracle),'actual native runtime import');print('E100e actual native CPU import PASS; no model/GPU');return
    p=argparse.ArgumentParser()
    for n in ('inputs','assets','assignment','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('input-sha','source-sha'):p.add_argument('--'+n,required=True)
    p.add_argument('--attempt-cap-seconds',type=float,default=DEFAULT_ATTEMPT_CAP,help='Default1800; nondefault is authorized attempt2 only, f599f121a measured-need bound and fresh output root')
    p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    verify(ROOT,str(a.source_seal.resolve().relative_to(ROOT)),a.source_sha);items,arrays=load(a.inputs,a.input_sha)
    if a.validate_only:print('E100e public168x2 native grid PASS');return
    ass=read(a.assignment);assignment(ass,a.input_sha,a.source_sha,sha(a.assets),a.attempt_cap_seconds,a.out);actual=hardware(ass)
    fresh_attempt(a.out);write(a.out/'ASSIGNMENT.json',ass);end=ass['absolute_deadline_epoch'];status='FAILED'
    timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    try:
        complete=acquire(items,arrays,backend(a.assets,ass),original().Clock(a.out,end-120),a.out,actual);status='COMPLETE' if complete else 'NO_FIT'
    except BaseException as exc:write(a.out/'FAILURE.json',dict(error_type=type(exc).__name__));raise
    finally:
        timer.cancel();write(a.out/'OUTPUT_SEAL.json',dict(experiment='E100e',status=status,input_sha256=a.input_sha,source_sha256=a.source_sha,pod_id=ass['pod_id'],gpu_type=actual,labels_on_pod=False,files={str(p.relative_to(a.out)):sha(p) for p in a.out.rglob('*') if p.is_file() and p.name!='OUTPUT_SEAL.json'}))
if __name__=='__main__':main()
