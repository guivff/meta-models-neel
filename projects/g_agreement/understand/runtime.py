"""Integrator-only operational admission and warmed batch timing for E1/E2/E7."""
import math
import os
import statistics
import time
from pathlib import Path
from .cpu import ROOT, read, sha, dump

CAPS={'E1':1440.,'E2':1080.,'E7':2880.}
PROGRAM_STOP_EPOCH=__import__('datetime').datetime(2026,10,27,22,59,tzinfo=__import__('datetime').timezone.utc).timestamp()
BRIEF='results/g_agreement/understand/BRIEF_UNDERSTAND.bound.md'


class Gate:
    def __init__(self,path,experiment):
        a=read(path);self.assignment=a;self.experiment=experiment
        if a.get('issuer')!='integrator' or a.get('experiment')!=experiment or a.get('gpu_count')!=1:
            raise ValueError('exact integrator experiment/one-GPU assignment required')
        if not a.get('pod_id') or a.get('external_hardstop_verified') is not True or a.get('hold_renewer_verified') is not True:
            raise ValueError('integrator pod/hardstop/hold-renewer evidence required')
        if a.get('brief_sha256')!=sha(ROOT/BRIEF) or a.get('brief_registered') is not True or a.get('brief_pushed') is not True:
            raise ValueError('registered pushed exploratory brief mismatch')
        required={str(p.relative_to(ROOT)) for p in (ROOT/'projects/g_agreement/understand').glob('*.py')}
        if not required<=set(a.get('source_files',{})):raise ValueError('complete exploratory source pins required')
        for f,d in a['source_files'].items():
            p=(ROOT/f).resolve()
            if not p.is_relative_to(ROOT) or sha(p)!=d:raise ValueError('source pin mismatch')
        keys=['allocated_gpu_seconds','previous_gpu_seconds','smoke_forecast_seconds','deadline_epoch','setup_deadline_epoch']
        if any(not isinstance(a.get(k),(int,float)) or not math.isfinite(a[k]) for k in keys):raise ValueError('finite timing fields required')
        self.allocation=float(a['allocated_gpu_seconds']);self.previous=float(a['previous_gpu_seconds'])
        cap=min(1.5*a['smoke_forecast_seconds']+360,CAPS[experiment])
        if a['smoke_forecast_seconds']<=0 or self.previous<0 or self.allocation<=180 or self.previous+self.allocation>cap:
            raise ValueError('cumulative exploratory science budget exceeded')
        if a.get('forecast_method')!='warmed_median_next_3_real_units':raise ValueError('warmed median forecast required')
        if a['deadline_epoch']>PROGRAM_STOP_EPOCH:raise ValueError('assignment beyond programme stop')
        if time.time()>=a['deadline_epoch']-180 or time.time()>=a['setup_deadline_epoch']:raise TimeoutError('assignment expired')
        if not 0<a.get('setup_allowance_seconds',0)<=2400:raise ValueError('guarded setup allowance required')
        created=a.get('provider_created_epoch')
        if not isinstance(created,(int,float)) or not math.isfinite(created) or not created<=time.time():raise ValueError('provider timestamp required')
        preceding=a.get('preceding_science_gpu_seconds',0)
        if not isinstance(preceding,(int,float)) or not math.isfinite(preceding) or preceding<0:raise ValueError('invalid preceding same-pod science')
        if a['setup_deadline_epoch']>created+a['setup_allowance_seconds']+preceding:raise ValueError('setup deadline beyond allowance plus preceding science')
        if a['deadline_epoch']>created+a['setup_allowance_seconds']+preceding+self.allocation:raise ValueError('science deadline beyond setup+preceding+allocation')
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')
        self.started=None;self.setup_complete=False

    def setup_guard(self):
        if self.started is not None:return self.guard()
        if hasattr(self,'setup_callback'):self.setup_callback()
        if time.time()>=self.assignment['setup_deadline_epoch']:raise TimeoutError('setup allowance exhausted')

    def start(self):
        if not self.setup_complete:self.setup_guard()
        if self.started is None:self.started=time.monotonic();self.first_science_epoch=time.time()
        self.guard()

    def guard(self):
        if self.started is None:self.setup_guard();return
        if time.time()>=self.assignment['deadline_epoch']-180 or time.monotonic()-self.started>=self.allocation-180:
            raise TimeoutError('science/retrieval deadline reached')


def run_batches(records,fn,batch,gate,out,already_warmed=False):
    """Load happens before this call. One discarded setup unit then three retained timings."""
    units=[records[i:i+batch] for i in range(0,len(records),batch)]
    if len(units)<3:raise ValueError('three real timed units required')
    if not already_warmed:
        gate.setup_guard();warm=max(units,key=lambda u:max(len(r.get('ids',r.get('text',''))) for r in u))
        discarded=fn(warm);del discarded;gate.setup_guard();gate.setup_complete=True
    elif not gate.setup_complete:raise ValueError('resident warm-up must be completed before science')
    gate.start()
    values=[];timings=[]
    for i,unit in enumerate(units):
        gate.guard();t=time.monotonic();value=fn(unit);elapsed=time.monotonic()-t
        values.append(value)
        if len(timings)<3:timings.append(elapsed)
        if len(timings)==3:
            median=statistics.median(timings)
            if not all(math.isfinite(x) and x>0 for x in timings):raise ValueError('invalid warmed timing')
            forecast=median*len(units)
            if i==2:dump(out/'WARMED_FORECAST.json',{'timed_unit_seconds':timings,'median_seconds':median,'forecast_seconds':forecast,'warmup_scored':False,'units':len(units)})
            remaining=1.5*median*(len(units)-i-1)+180
            if time.monotonic()-gate.started+remaining>gate.allocation:raise TimeoutError('NO_FIT: warmed remaining units exceed allocation')
        gate.guard()
    return values
