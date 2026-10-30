"""E24-E §137: six capture-only arms, immutable input/output and one shared custody cap."""
import argparse,importlib.util,inspect,json,os,signal,subprocess,sys,time
from collections import defaultdict
from pathlib import Path
from projects.g_agreement.blindspot import protocol as P
from .e24_diagnostic import original_module,records_for
from .e24_worker import read,seal
ARMS=('A','B','C','D','E','G')
TOTAL=2700
RESERVE=180

def layouts(items,selected,original):
    # Preserve original W1 neighbours, not merely its numerical batch size.
    chosen=set(selected);base=[b for b in original if chosen.intersection(b['ids'])]
    single=[{'unit':'selected','start':i,'ids':[uid]} for i,uid in enumerate(selected)]
    buckets=defaultdict(list)
    for uid in selected:buckets[len(items[uid]['ids'])].append(uid)
    exact=[]
    for length,ids in sorted(buckets.items()):
        for start in range(0,len(ids),32):exact.append({'unit':f'length:{length}','start':start,'ids':ids[start:start+32]})
    return {'A':base,'B':base,'C':single,'D':single,'E':exact,'G':base}

def capture_batch(arm,ol,batch,original,clone_capture):
    import mats.capture
    # Use the exact frozen W1 function; only G's requested layer literal changes.
    fn=original.capture_and_score
    if arm=='G':
        source=inspect.getsource(fn)
        if source.count('[42,44]')!=1:raise ValueError('W1 capture literal changed')
        ns={};exec(source.replace('[42,44]',repr(list(range(20,61,4)))),fn.__globals__,ns);fn=ns['capture_and_score']
    class Captured(Exception):pass
    result={}
    def done(h):result.update(h);raise Captured()
    previous=mats.capture.capture;mats.capture.capture=clone_capture
    try:
        try:fn(batch,None,{},ol,None,batch=1 if arm in ('C','D') else 32,on_capture=done)
        except Captured:pass
    finally:mats.capture.capture=previous
    if 44 not in result:raise ValueError('capture callback absent')
    return result

def cosines(a,b):
    import numpy as np
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('invalid vector shape/value')
    norms=np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)
    if (norms==0).any():raise ValueError('zero vector')
    return np.sum(a*b,axis=1)/norms

def decide(w1,cd,timings):
    if set(w1)!=set(ARMS):raise ValueError('all six arms required')
    import numpy as np
    n=len(cd)
    if not n or any(len(x)!=n for x in w1.values()):raise ValueError('unequal sample')
    if not all(np.isfinite(x).all() for x in [cd,*w1.values()]):raise ValueError('nonfinite cosine')
    suspect=bool(np.all(np.array(cd)>=.999) and np.any(np.array(w1['C'])<.999) and np.any(np.array(w1['D'])<.999))
    good=[k for k in ARMS if np.all(np.array(w1[k])>=.999)]
    if any(not np.isfinite(timings[k]) or timings[k]<=0 for k in ARMS):raise ValueError('invalid timing')
    mode=None if suspect or not good else ('G' if 'G' in good else min(good,key=lambda k:(timings[k],ARMS.index(k))))
    return {'status':'W1_REFERENCE_SUSPECT_HOLD_ALL_CAPTURE_DEPENDENT' if suspect else ('CAPTURE_MODE_CERTIFIED' if mode else 'NO_MODE_CERTIFIED'),
      'certified_arm':mode,'passing_arms':good,'automatic_relaunch':False,
      'selection':'G preferred when it passes; otherwise fastest complete arm on frozen population',
      'capture_seconds':timings,'below_0999':{k:int(np.sum(np.array(v)<.999)) for k,v in w1.items()}}

def analyse(out,bank,plan):
    import numpy as np
    P.verify(bank,'INPUT_SEAL.json')
    if P.sha(bank/'INPUT_SEAL.json')!=read(plan)['input_seal_sha256']:raise ValueError('analysis input binding')
    sel=read(bank/'selected.json');ids=[x['id'] for x in sel];vectors={};records={};times={}
    for arm in ARMS:
        dest=out/arm;P.verify(dest,'CAPTURE_SEAL.json');binding=read(dest/'BINDING.json')
        if binding['plan_sha256']!=P.sha(plan) or binding['input_seal_sha256']!=P.sha(bank/'INPUT_SEAL.json'):raise ValueError('arm binding')
        records[arm]=P.rows(dest/'records.jsonl')
        if [x['id'] for x in records[arm]]!=ids:raise ValueError('arm identity/order')
        vectors[arm]=np.load(dest/'acts44.npy',allow_pickle=False);times[arm]=read(dest/'TIMING.json')['capture_seconds']
    with (out/'ANALYSIS.lock').open('x') as f:f.write(P.sha(plan))
    ref=np.load(bank/'reference44.npy',mmap_mode='r',allow_pickle=False)[[x['reference_index'] for x in sel]]
    w1={k:cosines(v,ref) for k,v in vectors.items()};cd=cosines(vectors['C'],vectors['D'])
    result=decide(w1,cd,times);metrics=[];summaries={}
    for arm in ARMS:
        against_c=cosines(vectors[arm],vectors['C']);groups={}
        for field in ('token_count','padding_length','row'):
            group=defaultdict(lambda:{'n':0,'below_w1':0,'below_C':0})
            for i,x in enumerate(records[arm]):
                g=group[str(x[field])];g['n']+=1;g['below_w1']+=int(w1[arm][i]<.999);g['below_C']+=int(against_c[i]<.999)
            groups[field]=dict(group)
        summaries[arm]={'below_C':int(sum(against_c<.999)),'minimum_W1':float(min(w1[arm])),'minimum_C':float(min(against_c)),'failures_by':groups}
        for i,x in enumerate(records[arm]):metrics.append({**x,'cosine_W1':float(w1[arm][i]),'cosine_C':float(against_c[i])})
    P.jsonl(out/'metrics.jsonl',metrics);P.dump(out/'DECISION.json',result);P.dump(out/'STRATA.json',summaries)
    P.dump(out/'AUDIT_NEXT.json',{'status':'OWNER_IMPACT_AUDIT_REQUIRED_AFTER_REVIEW','runs':['E19','E22','E27c','E28','E30','E31ii','E33','E36'],
      'threshold':'fraction >0.10 => environment-qualified','do_not_rerun_or_alter_sealed_results':True,
      'if_no_condition':'report no condition identified and E28 score-level W1 parity delta <=0.006; do not invent a predicate'})
    seal(out,['metrics.jsonl','DECISION.json','STRATA.json','AUDIT_NEXT.json']+[f'{k}/CAPTURE_SEAL.json' for k in ARMS],'ANALYSIS_SEAL.json','E24E_ONCE_ONLY_CAPTURE_DIAGNOSTIC')

def child(a):
    import numpy as np
    import torch
    import importlib.metadata as md
    from projects.g_agreement.blindspot import run as W
    from . import e24_clone_capture
    q=read(a.assignment);plan=read(a.plan);env=q['environments'][a.environment]
    end=min(q['deadline_epoch'],q['provider_created_epoch']+TOTAL)-RESERVE
    def check():
        if time.time()>=end:raise TimeoutError('E24-E custody deadline')
    def expired(*_):raise TimeoutError('E24-E custody deadline')
    check();signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,end-time.time())
    if Path(sys.executable).absolute()!=Path(env['python']).absolute():raise ValueError('wrong environment interpreter')
    packages={d.metadata['Name'].lower():d.version for d in md.distributions() if d.metadata.get('Name')}
    for name,version in env['expected_packages'].items():
        if packages.get(name.lower())!=version:raise ValueError('environment pin mismatch: '+name)
    P.dump(a.out/f'ENV_{a.environment}.json',{'python':sys.version,'executable':sys.executable,'packages':packages,'evidence':env['reference_evidence'],'gpu':torch.cuda.get_device_name(0)})
    torch.set_num_threads(4);W._offline();assets=W._assets(a.assets,names=('model','olens'));original=original_module(plan)
    ol=original._load_oracle(assets);check()
    items={x['id']:x for x in P.rows(a.bank/'items.input.jsonl')};selection=read(a.bank/'selected.json');selected={x['id']:x for x in selection}
    layout=read(a.bank/'layout.json');ref=np.load(a.bank/'reference44.npy',mmap_mode='r',allow_pickle=False);refids=read(a.bank/'reference.order.json')
    for arm in (('A','C','G') if a.environment=='w1' else ('B','D','E')):
        dest=a.out/arm;dest.mkdir(exist_ok=False);rows=[];vectors=[];elapsed=0.
        for j,bb in enumerate(layout[arm]):
            check();batch=[items[uid] for uid in bb['ids']];torch.cuda.synchronize();start=time.monotonic()
            hs=capture_batch(arm,ol,batch,original,e24_clone_capture.capture);torch.cuda.synchronize();elapsed+=time.monotonic()-start
            rr,vv=records_for(hs[44].numpy(),batch,selected,ref,refids,bb,arm)
            np.save(dest/f'vectors_{j:04}.npy',np.stack(vv),allow_pickle=False)
            if arm=='G':
                positions=[i for i,x in enumerate(batch) if x['id'] in selected]
                np.savez(dest/f'grid_{j:04}.npz',**{str(k):h[positions].numpy() for k,h in hs.items()})
            with (dest/'records.partial.jsonl').open('a') as f:
                for x in rr:f.write(json.dumps(x,allow_nan=False)+'\n')
                f.flush();os.fsync(f.fileno())
            rows+=rr;vectors+=vv;check()
        keyed={x['id']:(x,v) for x,v in zip(rows,vectors)}
        if len(rows)!=len(selected) or set(keyed)!=set(selected):raise ValueError('incomplete selected population')
        ordered=[keyed[x['id']] for x in selection];P.jsonl(dest/'records.jsonl',[x for x,_ in ordered]);np.save(dest/'acts44.npy',np.stack([v for _,v in ordered]),allow_pickle=False)
        P.dump(dest/'TIMING.json',{'capture_seconds':elapsed,'forward_items':sum(len(b['ids']) for b in layout[arm]),'selected_items':len(selected),'includes_background_neighbours':arm in ('A','B','G')})
        P.dump(dest/'BINDING.json',{'plan_sha256':P.sha(a.plan),'input_seal_sha256':P.sha(a.bank/'INPUT_SEAL.json'),'assignment_sha256':P.sha(a.assignment),'arm':arm,'environment':a.environment})
        seal(dest,[p.name for p in dest.iterdir()],'CAPTURE_SEAL.json','E24E_CAPTURE_ONLY_CLONED')
    signal.setitimer(signal.ITIMER_REAL,0)

def validate_assignment(q,plan_hash,pod):
    if q.get('issuer')!='integrator' or q.get('experiment')!='E24-E' or not pod or q.get('pod_id')!=pod or q.get('plan_sha256')!=plan_hash:raise ValueError('assignment binding')
    if q.get('external_hardstop_verified') is not True or q.get('source_published') is not True or q.get('previous_e24e_gpu_seconds')!=0:raise ValueError('run-once/hardstop/publication requirement')
    if not 0<q['deadline_epoch']-q['provider_created_epoch']<=TOTAL:raise ValueError('0.75 GPUh custody cap')
    for key,path in [('w1','/weights/venv/bin/python'),('kernels','/weights/venv-kernels/bin/python')]:
        e=q['environments'][key]
        if e['python']!=path or not e.get('reference_evidence') or not {'torch','transformers','peft'}<=set(e['expected_packages']):raise ValueError('preserved environments required')

def run(a):
    q=read(a.assignment);plan=read(a.plan);validate_assignment(q,P.sha(a.plan),os.environ.get('RUNPOD_POD_ID'))
    for n,h in plan['source_files'].items():
        if P.sha(P.ROOT/n)!=h:raise ValueError('source changed: '+n)
    P.verify(a.bank,'INPUT_SEAL.json')
    if P.sha(a.bank/'INPUT_SEAL.json')!=plan['input_seal_sha256']:raise ValueError('input binding')
    with a.assignment.with_suffix('.e24e.lock').open('x') as f:f.write(P.sha(a.plan))
    a.out.mkdir(exist_ok=False,parents=True);proc=None;end=min(q['deadline_epoch'],q['provider_created_epoch']+TOTAL)-RESERVE
    try:
        for environment in ('w1','kernels'):
            command=[q['environments'][environment]['python'],'-m','projects.g_agreement.understand.e24_environment','child']
            for key in ('bank','plan','assignment','assets','out'):command+=['--'+key,str(getattr(a,key).resolve())]
            command+=['--environment',environment]
            with (a.out/f'{environment}.log').open('x') as log:
                proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                while proc.poll() is None:
                    if time.time()>=end:raise TimeoutError('shared custody deadline')
                    try:proc.wait(timeout=.5)
                    except subprocess.TimeoutExpired:pass
                if proc.returncode:raise RuntimeError('child failed: '+environment)
        for arm in ARMS:P.verify(a.out/arm,'CAPTURE_SEAL.json')
        seal(a.out,[f'{k}/CAPTURE_SEAL.json' for k in ARMS]+['ENV_w1.json','ENV_kernels.json'],'DIAGNOSTIC_SEAL.json','E24E_CAPTURE_COMPLETE_AWAIT_CPU_CERTIFICATION')
    except Exception as exc:
        P.dump(a.out/'FAILURE.json',{'status':'INCOMPLETE','reason':str(exc),'retry_authorized':False});raise
    finally:
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        P.dump(a.out/'RECEIPT.json',{'provider_elapsed_seconds':time.time()-q['provider_created_epoch'],'total_cap_s':TOTAL,'retrieval_reserve_s':RESERVE,'retry_authorized':False})

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['run','child','analyse'])
    for n in ('bank','plan','out'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('assignment','assets'):p.add_argument('--'+n,type=Path)
    p.add_argument('--environment',choices=['w1','kernels']);a=p.parse_args()
    if a.command=='analyse':analyse(a.out,a.bank,a.plan)
    elif a.command=='run':run(a)
    else:child(a)
