"""E22 integrator-only block-input patching; continuous warmed gate and sealed scores."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import statistics
import time
import numpy as np
import torch
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.budget import source_hashes as _source_hashes, _utc_seconds
from projects.g_agreement.understand.e19.run import persist, serial
from .inputs import load, ROWS

BATCH=16
CAP=10800.
SETUP=1500.
LAYERS=tuple(range(0,64,4))+(63,)
POSITIONS=('injection','preanswer')
ARMS=('opposite','same')
PROMPTS=tuple((row,prompt) for row in ROWS for prompt in ('asked','continuation')
              if prompt=='asked' or row!='prose_sentiment')


def source_hashes():
    result=_source_hashes()
    for experiment in ('e19','e22'):
        name=f'results/g_agreement/understand/{experiment}/REGISTRATION.md'
        result[name]=P.sha(P.ROOT/name)
    return result


def contract(data,row,prompt):
    indices=[i for i,item in enumerate(data['items']) if item['feature']==row]
    if len(indices)!=84:raise ValueError('exactly 84 test items per row required')
    if prompt=='asked':
        pairs=data['templates'][row]['olens'];prefix='';valid=list(range(len(pairs)))
    else:
        source=data['continuations']['rows'][row]
        pairs=[(p['A'],p['B']) for p in source['pairs']]
        prefix=data['continuations']['oracle_prefix'];valid=source['valid_pairs']
        if not pairs or not valid:raise ValueError('registered continuation endpoint unavailable')
    return indices,pairs,prefix,valid


def schedule(data):
    for row,prompt in PROMPTS:
        indices,_,_,_=contract(data,row,prompt)
        for layer in LAYERS:
            for position in POSITIONS:
                for arm in ARMS:
                    for start in range(0,len(indices),BATCH):
                        yield row,prompt,layer,position,arm,indices[start:start+BATCH]


def capture_bundle(runtime,data,row,prompt):
    indices,pairs,prefix,_=contract(data,row,prompt)
    captured={'recipient':runtime.capture(data['activations'][indices],pairs,prefix=prefix)}
    for arm in ARMS:
        mapping={r['recipient_index']:r['donor_index'] for r in data['donors'][arm]}
        ordered=[mapping[i] for i in indices]
        captured[arm]=runtime.capture(data['activations'][ordered],pairs,prefix=prefix)
    return captured


def baseline_record(captured,indices):
    return {arm:{'recipient_indices':indices,'scores':serial(value['scores']),
                 'per_pair_scores':serial(value['per_pair_scores']),
                 'layer_ids':list(value['layer_ids']),'metadata':value['metadata']}
            for arm,value in captured.items()}


def donor_indices(data,indices,recipients,arm):
    local={index:j for j,index in enumerate(indices)}
    mapping={r['recipient_index']:r['donor_index'] for r in data['donors'][arm]}
    return [local[mapping[i]] for i in recipients]


def unit(runtime,data,captured,spec):
    row,prompt,layer,position,arm,recipients=spec
    indices,pairs,prefix,valid=contract(data,row,prompt)
    local={index:j for j,index in enumerate(indices)}
    donor=donor_indices(data,indices,recipients,arm)
    ordered=[local[i] for i in recipients]
    patched=runtime.score_patch(data['activations'][recipients],pairs,captured[arm],layer,position,
                                prefix=prefix,donor_indices=ordered)
    if layer==0 and position=='injection' and not torch.equal(patched['per_pair_scores'],captured[arm]['per_pair_scores'][ordered]):
        raise ValueError('layer0 patch differs from matching-layout full-swap baseline')
    records=[]
    for j,i in enumerate(recipients):
        item=data['items'][i];d=indices[donor[j]]
        record={'row':row,'prompt':prompt,'layer':layer,'position':position,'arm':arm,
                'item_id':item['id'],'cluster':item['cluster'],'donor_id':data['items'][d]['id']}
        for name,value in (('recipient',captured['recipient']['per_pair_scores'][local[i]]),
                           ('donor',captured[arm]['per_pair_scores'][local[i]]),
                           ('patched',patched['per_pair_scores'][j])):
            record[name+'_pair_scores']=serial(value)
            record[name+'_score']=float(value[valid].mean())
        records.append(record)
    return records


def swap_check(runtime,data,captured,row,prompt):
    indices,pairs,prefix,_=contract(data,row,prompt)
    recipients=indices[:4];receipts=[]
    for arm in ARMS:
        donor=donor_indices(data,indices,recipients,arm)
        full=runtime.capture(data['activations'][[indices[d] for d in donor]],pairs,prefix=prefix)
        patch=runtime.score_patch(data['activations'][recipients],pairs,captured[arm],0,'injection',
                                  prefix=prefix,donor_indices=list(range(len(recipients))))
        a,b=full['per_pair_scores'],patch['per_pair_scores']
        receipts.append({'arm':arm,'recipient_ids':[data['items'][i]['id'] for i in recipients],
                         'full_swap_pair_scores':serial(a),'patch_pair_scores':serial(b),
                         'max_abs_difference':float((a-b).abs().max()),'exact_equal':bool(torch.equal(a,b))})
    return {'row':row,'prompt':prompt,'passed':all(r['exact_equal'] for r in receipts),'checks':receipts}


class Clock:
    def __init__(self,assignment,out,bindings):
        a=json.loads(Path(assignment).read_text())
        for k,v in {'experiment':'E22','gpu_count':1,'max_science_seconds':CAP,'setup_allowance_seconds':SETUP,
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
        if left<=0:raise TimeoutError('E22 allowance exhausted')
        def stop(*_):raise TimeoutError('E22 continuous deadline reached')
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
        if time.time()>=self.deadline or time.monotonic()-self.first>=self.state['science_cap_seconds']:raise TimeoutError('E22 cap exhausted')
    def gate(self,forecasts):
        if 'gate' in self.state:raise ValueError('gate already evaluated')
        if len(forecasts)!=len(PROMPTS) or any(not math.isfinite(f) or f<=0 for f in forecasts):raise ValueError('nine positive finite row/prompt forecasts required')
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



def run(inputs,assets,assignment,out,device='cuda'):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    bindings={'input_seal_sha256':P.sha(Path(inputs)/'INPUT_SEAL.json')}
    clock=Clock(assignment,out,bindings);status='COMPLETE';error=None
    (out/'scores.jsonl').touch(exist_ok=False)
    (out/'units').mkdir();(out/'baselines').mkdir();(out/'calibration').mkdir()
    try:
        with clock.setup():
            data=load(inputs)
            if data['provenance']['registration_sha256']!=P.sha(P.ROOT/'results/g_agreement/understand/e22/REGISTRATION.md'):
                raise ValueError('input registration differs from pinned E22 registration')
            plan=list(schedule(data))
            persist(out/'manifest.json',{'expected_items':data['items'],'unit_count':len(plan),
                    'batch':BATCH,'layer_ids':list(LAYERS),'positions':list(POSITIONS),
                    'prompts':PROMPTS,'arms':ARMS,'layer_convention':'zero-based decoder block INPUT'})
            persist(out/'provenance.json',{'experiment':'E22',**bindings,'source_files':source_hashes(),
                    'registration_sha256':P.sha(P.ROOT/'results/g_agreement/understand/e22/REGISTRATION.md'),
                    'inputs':str(inputs),'score_orientation':'A-minus-B; donor sign applied only in analysis'})
            from projects.g_agreement.understand.reader_runtime import load_runtime
            from .runtime import E22Runtime
            runtime=E22Runtime(load_runtime('olens',assets,device=device),candidate_batch=32)
            from mats.capture import decoder_blocks
            if len(decoder_blocks(runtime.oracle.model))!=64:raise ValueError('pinned 64-block reader required')
            for row,prompt in PROMPTS:
                if prompt=='continuation':
                    for pair in data['continuations']['rows'][row]['pairs']:
                        for side in ('A','B'):
                            if runtime.oracle.reader.tok.encode(pair[side],add_special_tokens=False)!=pair[side+'_ids']:
                                raise ValueError('E15 candidate token IDs differ from frozen pairs')
        clock.start();forecasts=[]
        for row,prompt in PROMPTS:
            indices,pairs,prefix,_=contract(data,row,prompt)
            spec=(row,prompt,LAYERS[-1],'preanswer','opposite',indices[:BATCH])
            clock.check();captured=capture_bundle(runtime,data,row,prompt)
            unit(runtime,data,captured,spec);clock.check()
            parity=swap_check(runtime,data,captured,row,prompt)
            persist(out/'calibration'/f'{row}.{prompt}.swap_check.json',parity)
            clock.check()
            if not parity['passed']:raise ValueError('layer0 injection patch differs from full activation swap')
            times_capture=[];times_patch=[]
            for repeat in range(3):
                del captured
                clock.check();start=time.monotonic()
                captured=capture_bundle(runtime,data,row,prompt)
                persist(out/'calibration'/f'{row}.{prompt}.baseline_{repeat}.json',baseline_record(captured,indices))
                clock.check();times_capture.append(time.monotonic()-start)
                start=time.monotonic();records=unit(runtime,data,captured,spec)
                persist(out/'calibration'/f'{row}.{prompt}.patch_{repeat}.json',records)
                clock.check();times_patch.append(time.monotonic()-start)
            units=sum(s[0:2]==(row,prompt) for s in plan)
            forecast=statistics.median(times_capture)+units*statistics.median(times_patch)
            forecasts.append(forecast)
            persist(out/'calibration'/f'{row}.{prompt}.timing.json',{'baseline_timings':times_capture,
                    'patch_timings':times_patch,'patch_units':units,'baseline_bundle_units':1,'captures_per_bundle':3,'forecast_seconds':forecast})
            del captured
        persist(out/'calibration/GATE.json',clock.gate(forecasts))
        ordinal=0
        for row,prompt in PROMPTS:
            indices,pairs,prefix,_=contract(data,row,prompt)
            clock.check();captured=capture_bundle(runtime,data,row,prompt)
            persist(out/'baselines'/f'{row}.{prompt}.json',baseline_record(captured,indices));clock.check()
            for spec in (s for s in plan if s[:2]==(row,prompt)):
                records=unit(runtime,data,captured,spec);clock.check()
                persist(out/'units'/f'{ordinal:05d}.json',records);clock.check();ordinal+=1
            del captured
    except Exception as exc:
        status='INCOMPLETE';error=type(exc).__name__+': '+str(exc)
    finally:
        clock.disarm()
        with (out/'scores.jsonl').open('w') as f:
            for path in sorted((out/'units').glob('*.json')):
                for record in json.loads(path.read_text()):f.write(json.dumps(record,allow_nan=False)+'\n')
        if clock.first is not None and time.monotonic()-clock.first>clock.state['science_cap_seconds']:
            status='INCOMPLETE_CAP_OVERRUN'
        persist(out/'RUN_STATUS.json',{'experiment':'E22','status':status,'error':error,'exploratory':True})
        files=[str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()
               and p.name not in ('allocation.lock','budget.json') and p.suffix!='.tmp']
        P.seal(out,files,'SCORES_SEALED_EXPLORATORY_E22');clock.close(status)
    return {'status':status,'error':error,'score_seal_sha256':P.sha(out/'SCORE_SEAL.json')}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','assets','assignment','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--device',default='cuda')
    print(json.dumps(run(**vars(p.parse_args())),indent=2))

if __name__=='__main__':main()
