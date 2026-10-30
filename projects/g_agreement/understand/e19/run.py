"""Integrator-only E19 inference; dev directions must already be committed."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import time
import numpy as np
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot.w7_steering import random_vectors
from projects.g_agreement.understand.budget import source_hashes as _source_hashes, _utc_seconds
from .inputs import load, ROWS, ALPHAS, RANDOM_DIRECTION_SEEDS
from .freeze import load_freeze

BATCH = 16
CAP = 9000.
SETUP = 1500.
CONTENT = 'prose_sentiment'


def source_hashes():
    result=_source_hashes()
    name='results/g_agreement/understand/e19/REGISTRATION.md'
    result[name]=P.sha(P.ROOT/name)
    return result


def arms(row):
    return ['own']+['random_'+str(s) for s in RANDOM_DIRECTION_SEEDS]+(['content'] if row!=CONTENT else [])+['donor']


def schedule(data):
    for row in ROWS:
        indices=[i for i,it in enumerate(data['items']) if it['feature']==row]
        for arm in arms(row):
            for alpha in ALPHAS:
                for start in range(0,len(indices),BATCH):
                    yield row,arm,alpha,indices[start:start+BATCH]


def vector(row,arm,directions):
    own=directions[row]['u']
    if arm.startswith('random_'):
        # Reuse W7's isotropic equal-norm control construction, one draw/seed.
        return random_vectors(own,seed=int(arm.split('_')[1]))[0]
    return directions[CONTENT]['u'] if arm=='content' else own


def serial(value):
    if hasattr(value,'detach'):return value.detach().cpu().tolist()
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [serial(v) for v in value]
    return value


def unit(runtime,data,directions,spec):
    row,arm,alpha,ix=spec
    donors={r['recipient_index']:r['donor_index'] for r in data['donors']}
    source=[donors[i] for i in ix] if arm=='donor' else ix
    h=np.array(data['activations'][source],copy=True)
    d=directions[row]
    kwargs=dict(layer=d['layer'],direction=vector(row,arm,directions),sigma=d['sigma'],alpha=alpha,projection_direction=d['u'])
    asked=runtime.score(h,data['templates'][row]['olens'],**kwargs)
    continuation=data['continuations']['rows'][row]
    cont=None
    if continuation['pairs']:
        cont=runtime.score(h,[(p['A'],p['B']) for p in continuation['pairs']],prefix=data['continuations']['oracle_prefix'],**kwargs)
    results=[]
    for j,i in enumerate(ix):
        item=data['items'][i]
        rec={'row':row,'item_id':item['id'],'cluster':item['cluster'],'arm':arm,'alpha':alpha,
             'injected_item_id':data['items'][source[j]]['id'],'layer':d['layer'],'sigma':d['sigma'],
             'asked_score':float(asked['scores'][j]),'asked_pair_scores':serial(asked['per_pair_scores'][j]),
             'projection_preanswer':float(asked['projection_preanswer'][j].mean()),
             'projection_answer_mean':float(asked['projection_answer_mean'][j].mean()),
             'asked_projection_details':[serial(r) for r in asked['projections'] if r['item_index']==j],
             'continuation_score':None,'continuation_status':continuation['primary_status']}
        if cont is not None:
            pairs=cont['per_pair_scores'][j]
            valid=continuation['valid_pairs']
            rec.update(continuation_pair_scores=serial(pairs),continuation_all_pairs_score=float(pairs.mean()),
                       continuation_score=float(pairs[valid].mean()) if valid else None,
                       continuation_projection_preanswer=float(cont['projection_preanswer'][j].mean()),
                       continuation_projection_answer_mean=float(cont['projection_answer_mean'][j].mean()),
                       continuation_projection_details=[serial(r) for r in cont['projections'] if r['item_index']==j])
        results.append(rec)
    return results


def persist(path,value):
    tmp=path.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(value,f,sort_keys=True,allow_nan=False);f.write('\n');f.flush()
        import os
        os.fsync(f.fileno())
    tmp.replace(path)
    return P.sha(path)


class Clock:
    def __init__(self,assignment,out,bindings):
        a=json.loads(Path(assignment).read_text())
        for k,v in {'experiment':'E19','gpu_count':1,'max_science_seconds':CAP,'setup_allowance_seconds':SETUP,
                    'source_files':source_hashes(),**bindings}.items():
            if a.get(k)!=v:raise ValueError('assignment mismatch: '+k)
        if not a.get('pod_id') or a.get('external_hard_stop_verified') is not True:raise ValueError('external guard required')
        if os.environ.get('RUNPOD_POD_ID')!=a['pod_id']:raise ValueError('assignment pod differs from RUNPOD_POD_ID')
        self.deadline=_utc_seconds(a['hard_deadline_utc'])
        self.out=Path(out);self.old=signal.getsignal(signal.SIGALRM)
        self.lock=(self.out/'allocation.lock').open('x')
        fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        self.state={'setup_seconds':0.,'science_seconds':0.,'science_cap_seconds':CAP,'status':'SETUP'}
        self.first=None
    def save(self):persist(self.out/'budget.json',self.state)
    def arm(self,seconds):
        left=min(seconds,self.deadline-time.time())
        if left<=0:raise TimeoutError('E19 allowance exhausted')
        def stop(*_):raise TimeoutError('E19 continuous deadline reached')
        signal.signal(signal.SIGALRM,stop);signal.setitimer(signal.ITIMER_REAL,left)
    def disarm(self):signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,self.old)
    @contextmanager
    def setup(self):
        start=time.monotonic();self.arm(SETUP)
        try:yield
        finally:
            self.disarm();self.state['setup_seconds']=time.monotonic()-start;self.save()
    def start(self):
        if self.first is not None or self.state['setup_seconds']>SETUP:raise ValueError('cannot restart or exceed setup')
        self.first=time.monotonic();self.state['status']='SCIENCE';self.arm(CAP);self.save()
    def check(self):
        if time.time()>=self.deadline or time.monotonic()-self.first>=self.state['science_cap_seconds']:raise TimeoutError('E19 cap exhausted')
    def gate(self,forecasts):
        if 'gate' in self.state:raise ValueError('gate already evaluated')
        if len(forecasts)!=len(ROWS) or any(not math.isfinite(f) or f<=0 for f in forecasts):raise ValueError('five positive finite row forecasts required')
        self.check();f=sum(forecasts);used=time.monotonic()-self.first
        cap=min(1.5*f+360,CAP)
        gate={'forecast_seconds':f,'science_consumed_seconds':used,'science_cap_seconds':cap,'admitted':used+f<=cap}
        self.state.update(science_cap_seconds=cap,gate=gate);self.save()
        if not gate['admitted']:raise RuntimeError('NO_GO_WARMED_FORECAST')
        self.arm(cap-used);return gate
    def close(self,status):
        self.disarm()
        self.state.update(status=status,science_seconds=0. if self.first is None else time.monotonic()-self.first)
        self.state['cap_overrun_seconds']=max(0.,self.state['science_seconds']-self.state['science_cap_seconds'])
        self.save();self.lock.close()


def verify_committed_freeze(freeze,commit):
    freeze=Path(freeze).resolve()
    _,directions=load_freeze(freeze)
    # A byte-identical copy may be staged anywhere; git object paths are fixed.
    for name in ('FREEZE.json','directions.npz','FREEZE_SEAL.json'):
        path='results/g_agreement/understand/e19/freeze/'+name
        blob=subprocess.check_output(['git','show',commit+':'+path],cwd=P.ROOT)
        if hashlib.sha256(blob).hexdigest()!=P.sha(freeze/name):raise ValueError('freeze differs from committed bytes')
    return directions


def run(inputs,freeze,freeze_commit,assets,assignment,out,device='cuda'):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    bindings={'input_seal_sha256':P.sha(Path(inputs)/'INPUT_SEAL.json'),
              'freeze_seal_sha256':P.sha(Path(freeze)/'FREEZE_SEAL.json'),'freeze_commit':freeze_commit}
    clock=Clock(assignment,out,bindings);runtime=None;status='COMPLETE';error=None
    (out/'scores.jsonl').touch(exist_ok=False)
    try:
        with clock.setup():
            directions=verify_committed_freeze(freeze,freeze_commit)
            data=load(inputs)
            frozen,_=load_freeze(freeze)
            if frozen['source']['e3_input_seal_sha256']!=data['provenance']['source_e3_input_seal_sha256']:raise ValueError('E3 input/freeze lineage mismatch')
            plan=list(schedule(data));(out/'units').mkdir();(out/'calibration').mkdir()
            persist(out/'manifest.json',{'expected_items':data['items'],'unit_count':len(plan),'batch':BATCH,'rows':list(ROWS),'alphas':list(ALPHAS)})
            persist(out/'provenance.json',{'experiment':'E19',**bindings,'source_files':source_hashes(),'score_orientation':'A-minus-B; no flips',
                    'continuation_unavailable':['prose_sentiment'],'inputs':str(inputs)})
            from projects.g_agreement.understand.reader_runtime import load_runtime
            from .runtime import E19Runtime
            runtime=E19Runtime(load_runtime('olens',assets,device=device))
            for row in ROWS:
                for pair in data['continuations']['rows'][row]['pairs']:
                    for side in ('A','B'):
                        if runtime.oracle.reader.tok.encode(pair[side],add_special_tokens=False)!=pair[side+'_ids']:
                            raise ValueError('E15 frozen tokenizer IDs mismatch')
        clock.start();forecasts=[]
        for row in ROWS:
            spec=next(u for u in plan if u[0]==row and u[1]=='own' and u[2]==4)
            clock.check();unit(runtime,data,directions,spec);clock.check()
            times=[]
            for repeat in range(3):
                clock.check();start=time.monotonic();values=unit(runtime,data,directions,spec)
                persist(out/'calibration'/(row+f'.timing_unit_{repeat}.json'),values)
                clock.check();times.append(time.monotonic()-start)
            n=sum(u[0]==row for u in plan);forecast=statistics.median(times)*n;forecasts.append(forecast)
            persist(out/'calibration'/(row+'.json'),{'warmups':1,'timings_seconds':times,'units':n,'forecast_seconds':forecast})
        persist(out/'calibration/GATE.json',clock.gate(forecasts))
        for i,spec in enumerate(plan):
            clock.check();records=unit(runtime,data,directions,spec);clock.check()
            persist(out/'units'/f'{i:05d}.json',records);clock.check()
    except Exception as exc:
        status='INCOMPLETE';error=type(exc).__name__+': '+str(exc)
    finally:
        clock.disarm() # After failure, no further model operations; seal every retained unit on CPU.
        if clock.first is not None:
            with (out/'scores.jsonl').open('w') as f:
                for path in sorted((out/'units').glob('*.json')):
                    for record in json.loads(path.read_text()):f.write(json.dumps(record,allow_nan=False)+'\n')
        if clock.first is not None and time.monotonic()-clock.first>clock.state['science_cap_seconds']:
            status='INCOMPLETE_CAP_OVERRUN'
        persist(out/'RUN_STATUS.json',{'experiment':'E19','status':status,'error':error,'exploratory':True})
        files=[str(p.relative_to(out)) for p in out.rglob('*') if p.is_file() and p.name not in ('allocation.lock','budget.json') and p.suffix!='.tmp']
        # A single immutable score seal; post-seal custody timing is in budget.json.
        P.seal(out,files,'SCORES_SEALED_EXPLORATORY_E19')
        clock.close(status)
    return {'status':status,'error':error,'score_seal_sha256':P.sha(out/'SCORE_SEAL.json')}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','freeze','assets','assignment','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--freeze-commit',required=True);p.add_argument('--device',default='cuda')
    a=p.parse_args();print(json.dumps(run(**vars(a)),indent=2))

if __name__=='__main__':main()
