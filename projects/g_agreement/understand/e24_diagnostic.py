"""E24-D: capture-only four-arm diagnostic; no E24 retry or reader scoring."""
import argparse
import importlib.util
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import textwrap
import time
from projects.g_agreement.blindspot import protocol as P, run as W
from .e24_worker import Engine, PRIORITY, read, seal

CAP,SETUP,TOTAL,RESERVE=1800,1500,2160,180


def deadline(q,clock,now):
    absolute=min(q['deadline_epoch'],q['provider_created_epoch']+TOTAL)-RESERVE
    return min(absolute,clock['first_science_epoch']+CAP if clock else q['provider_created_epoch']+SETUP)


def diagnose(arms):
    a=arms['a'];bad_a=[x['id'] for x in a if x['cosine']<.999]
    if bad_a:return {'status':'REFERENCE_FAILURE_STOP','failed_a':bad_a,'cause':'reference not reproduced by original capture/layout/environment','relaunch_eligible':False}
    if set(arms)!={'a','b','c','d'}:return {'status':'INCOMPLETE','relaunch_eligible':False}
    by={k:{x['id']:x for x in v} for k,v in arms.items()}
    if any(set(v)!=set(by['a']) or len(v)!=len(arms[k]) for k,v in by.items()):raise ValueError('arm identity mismatch')
    failed=[uid for uid,x in by['b'].items() if x['cosine']<.999]
    matches={'alignment':[],'batching':[],'environment':[]}
    for uid in failed:
        x=by['b'][uid]
        if x['best_reference_index']!=x['reference_index']:matches['alignment'].append(uid)
        if by['c'][uid]['cosine']>=.999:matches['batching'].append(uid)
        if by['d'][uid]['cosine']>=.999:matches['environment'].append(uid)
    causes=[k for k,v in matches.items() if failed and len(v)==len(failed)]
    unique=len(causes)==1
    return {'status':'CAUSE_NAMED_REVIEW_FIX_REQUIRED' if unique else 'INCONCLUSIVE',
        'b_failed_ids':failed,'itemwise_rule_matches':matches,'global_rule_matches':causes,
        'cause':causes[0] if unique else None,'relaunch_eligible':unique,
        'automatic_relaunch':False,'requirement':'one reviewed cause-limited diff before the single E24 retry; inconclusive closes E24 INCOMPLETE'}


def original_module(plan):
    path=P.ROOT/plan['w1_capture_module']
    spec=importlib.util.spec_from_file_location('projects.g_agreement.blindspot._e24d_original',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


def capture_batch(arm,ol,batch,original):
    if arm=='a':
        class Captured(Exception):pass
        result={}
        def done(h):result.update(h);raise Captured()
        try:original.capture_and_score(batch,None,{},ol,None,batch=32,on_capture=done)
        except Captured:pass
        if not result:raise ValueError('W1 original capture callback missing')
        return result[44]
    engine=object.__new__(Engine);engine.ol=ol
    if arm=='c':
        # Exact existing method, with only its literal capture batch size changed.
        source=textwrap.dedent(inspect.getsource(Engine.capture))
        if source.count('batch_size=8')!=1:raise ValueError('E24 capture source changed')
        ns={};exec(source.replace('batch_size=8','batch_size=1'),Engine.capture.__globals__,ns)
        return ns['capture'](engine,batch,list(PRIORITY))[44]
    return engine.capture(batch,list(PRIORITY))[44]


def records_for(h,batch,selected,ref,refids,layout,arm):
    import numpy as np
    width=max(len(x['ids']) for x in batch);records=[];vectors=[]
    for pos,x in enumerate(batch):
        if x['id'] not in selected:continue
        z=np.asarray(h[pos],dtype=np.float64);index=selected[x['id']]['reference_index']
        if not np.isfinite(z).all() or np.linalg.norm(z)==0:raise ValueError('invalid fresh vector')
        v=np.asarray(ref[index],dtype=np.float64)
        cosine=float(z@v/(np.linalg.norm(z)*np.linalg.norm(v)))
        best=None;bestcos=None
        if cosine<.999:
            # Search every reference index, not merely the 300 selected items.
            scores=[]
            for start in range(0,len(ref),256):
                block=np.asarray(ref[start:start+256],dtype=np.float64)
                scores.extend((block@z/(np.linalg.norm(block,axis=1)*np.linalg.norm(z))).tolist())
            best=int(np.argmax(scores));bestcos=float(scores[best])
        records.append({'id':x['id'],'row':x['feature'],'arm':arm,'token_count':len(x['ids']),
            'padding_length':width-len(x['ids']),'batch_position':pos,'batch_size':len(batch),
            'batch_unit':layout['unit'],'batch_start':layout['start'],'reference_index':index,
            'reference_id':refids[index],'cosine':cosine,'best_reference_index':best,
            'best_reference_id':None if best is None else refids[best],'best_cosine':bestcos})
        vectors.append(z.astype(np.float32))
    return records,vectors


def run_child(a):
    import numpy as np
    import torch
    import importlib.metadata as metadata
    torch.set_num_threads(4)
    q=read(a.assignment);plan=read(a.plan);clock=a.out/'CLOCK.json';check=lambda:None
    def check():
        end=deadline(q,read(clock) if clock.exists() else None,time.time())
        if time.time()>=end:raise TimeoutError('E24-D shared setup/science/custody exhausted')
        signal.setitimer(signal.ITIMER_REAL,max(.01,end-time.time()))
    def expired(*_):raise TimeoutError('E24-D absolute deadline')
    signal.signal(signal.SIGALRM,expired);check()
    env=q['environments'][a.environment]
    if str(Path(sys.executable).resolve())!=str(Path(env['python']).resolve()):raise ValueError('wrong interpreter')
    packages={dist.metadata['Name'].lower():dist.version for dist in metadata.distributions() if dist.metadata.get('Name')}
    for name,version in env['expected_packages'].items():
        if packages.get(name.lower())!=version:raise ValueError('environment package mismatch: '+name)
    P.dump(a.out/f'ENV_{a.environment}.json',{'python':sys.version,'executable':sys.executable,'packages':packages,'environment_evidence':env['reference_evidence'],'gpu':torch.cuda.get_device_name(0)})
    assets=W._assets(a.assets,names=('model','olens'));original=original_module(plan)
    ol=(original._load_oracle if a.environment=='w1' else W._load_oracle)(assets);check()
    items={x['id']:x for x in P.rows(a.bank/'items.input.jsonl')};selection=read(a.bank/'selected.json');selected={x['id']:x for x in selection}
    layout=read(a.bank/'layout.json');ref=np.load(a.bank/'reference44.npy',mmap_mode='r',allow_pickle=False);refids=read(a.bank/'reference.order.json')
    for arm in (('a','d') if a.environment=='w1' else ('b','c')):
        dest=a.out/arm;dest.mkdir(exist_ok=False);rows=[];vectors=[]
        for j,bb in enumerate(layout[arm]):
            check()
            if not clock.exists():
                tmp=clock.with_suffix('.tmp');P.dump(tmp,{'first_science_epoch':time.time(),'provider_created_epoch':q['provider_created_epoch']});tmp.replace(clock)
            check();batch=[items[uid] for uid in bb['ids']]
            h=capture_batch(arm,ol,batch,original);torch.cuda.synchronize();check()
            rr,vv=records_for(h.numpy(),batch,selected,ref,refids,bb,arm)
            # Save vectors and metadata before judging or advancing to another arm.
            np.save(dest/f'vectors_{j:04}.npy',np.stack(vv),allow_pickle=False)
            with (dest/'records.partial.jsonl').open('a') as f:
                for x in rr:f.write(json.dumps(x,allow_nan=False)+'\n')
                f.flush();os.fsync(f.fileno())
            rows+=rr;vectors+=vv;check()
        keyed={x['id']:(x,v) for x,v in zip(rows,vectors)}
        if len(rows)!=300 or set(keyed)!=set(selected):raise ValueError('selected population incomplete')
        ordered=[keyed[x['id']] for x in selection]
        P.jsonl(dest/'records.jsonl',[x for x,_ in ordered]);np.save(dest/'acts44.npy',np.stack([v for _,v in ordered]),allow_pickle=False)
        P.dump(dest/'BINDING.json',{'plan_sha256':P.sha(a.plan),'input_seal_sha256':P.sha(a.bank/'INPUT_SEAL.json'),'assignment_sha256':P.sha(a.assignment),'arm':arm,'environment':a.environment})
        seal(dest,['records.jsonl','acts44.npy','BINDING.json'],'CAPTURE_SEAL.json','E24D_CAPTURE_ONLY_NO_SCORES')
        if arm=='a' and any(x['cosine']<.999 for x in rows):
            P.dump(a.out/'DIAGNOSIS.json',diagnose({'a':rows}));return
    signal.setitimer(signal.ITIMER_REAL,0)


def run(a):
    q=read(a.assignment);plan=read(a.plan)
    if (q.get('issuer')!='integrator' or q.get('experiment')!='E24-D' or q.get('pod_id')!=os.environ.get('RUNPOD_POD_ID') or not q.get('pod_id')
        or q.get('plan_sha256')!=P.sha(a.plan) or q.get('external_hardstop_verified') is not True or q.get('source_published') is not True
        or q.get('w1_environment_matches_reference') is not True or q.get('previous_diagnostic_gpu_seconds')!=0):raise ValueError('bound E24-D integrator assignment required')
    if not 0<q['deadline_epoch']-q['provider_created_epoch']<=TOTAL:raise ValueError('custody exceeds0.6GPUh')
    for key in ('w1','kernels'):
        env=q['environments'][key]
        if not env.get('reference_evidence') or not {'torch','transformers','peft'}<=set(env['expected_packages']):raise ValueError('preserved environment evidence required')
    if q['environments']['kernels']['python']!='/weights/venv-kernels/bin/python':raise ValueError('original E24 kernel environment required')
    for n,h in plan['source_files'].items():
        if P.sha(P.ROOT/n)!=h:raise ValueError('source changed: '+n)
    P.verify(a.bank,'INPUT_SEAL.json')
    if P.sha(a.bank/'INPUT_SEAL.json')!=plan['input_seal_sha256']:raise ValueError('input binding')
    with a.assignment.with_suffix('.e24d.lock').open('x') as f:f.write(P.sha(a.plan))
    a.out.mkdir(exist_ok=False,parents=True);clock=a.out/'CLOCK.json';start=time.time();proc=None
    try:
        for environment in ('w1','kernels'):
            command=[q['environments'][environment]['python'],'-m','projects.g_agreement.understand.e24_diagnostic','child']
            for key in ('bank','plan','assignment','assets','out'):command+=['--'+key,str(getattr(a,key).resolve())]
            command+=['--environment',environment]
            with (a.out/f'{environment}.log').open('x') as log:
                proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                while proc.poll() is None:
                    if time.time()>=deadline(q,read(clock) if clock.exists() else None,time.time()):raise TimeoutError('shared diagnostic deadline')
                    try:proc.wait(timeout=.5)
                    except subprocess.TimeoutExpired:pass
                if proc.returncode:raise RuntimeError('diagnostic child failed: '+environment)
            if (a.out/'DIAGNOSIS.json').exists():break
        if not (a.out/'DIAGNOSIS.json').exists():
            arms={}
            for arm in 'abcd':P.verify(a.out/arm,'CAPTURE_SEAL.json');arms[arm]=P.rows(a.out/arm/'records.jsonl')
            P.dump(a.out/'DIAGNOSIS.json',diagnose(arms))
        names=['DIAGNOSIS.json']+[str(p.relative_to(a.out)) for p in a.out.glob('*/CAPTURE_SEAL.json')]+[p.name for p in a.out.glob('ENV_*.json')]
        seal(a.out,names,'DIAGNOSTIC_SEAL.json','E24D_COMPLETE_NO_AUTOMATIC_RELAUNCH')
    except Exception as exc:
        P.dump(a.out/'FAILURE.json',{'status':'INCOMPLETE','reason':str(exc),'retry_authorized':False});raise
    finally:
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        now=time.time();c=read(clock) if clock.exists() else None
        P.dump(a.out/'RECEIPT.json',{'setup_seconds':(c['first_science_epoch'] if c else now)-q['provider_created_epoch'],
            'science_seconds':0 if not c else now-c['first_science_epoch'],'provider_elapsed_seconds':now-q['provider_created_epoch'],
            'e24_attempt1_gpu_hours':1.45,'diagnostic_counts_toward_e24_total':True,'e24_total_gpu_hours_cap':12})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['run','child'])
    for n in ('bank','plan','assignment','assets','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--environment',choices=['w1','kernels']);a=p.parse_args()
    if a.command=='run':run(a)
    else:run_child(a)
