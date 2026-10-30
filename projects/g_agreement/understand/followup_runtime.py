"""Separate §99/§102 admission; preserves the sealed E7 retry's runtime bytes."""
import math
import os
import statistics
import time
from pathlib import Path
from .cpu import ROOT,read,dump,sha,seal

CAPS={'E1b':1440.,'E12':3600.}
STOP=__import__('datetime').datetime(2026,10,28,22,59,tzinfo=__import__('datetime').timezone.utc).timestamp()
BRIEF='results/g_agreement/understand/e1b/BRIEF_UNDERSTAND.authority.md'
REQUIRED={'projects/g_agreement/understand/'+n+'.py' for n in ['followup_runtime','followup_prepare','followup_packed','followup_analyse','e12','cpu']}


class Gate:
    def __init__(self,path,experiment):
        a=read(path);self.assignment=a;self.experiment=experiment;self.started=None;self.phases={}
        if a.get('issuer')!='integrator' or a.get('experiment')!=experiment or a.get('gpu_count')!=1 or not a.get('pod_id'):raise ValueError('exact integrator one-pod assignment required')
        for k in ['external_hardstop_verified','hold_renewer_verified','brief_registered','brief_pushed']:
            if a.get(k) is not True:raise ValueError(k+' evidence required')
        if a.get('brief_sha256')!=sha(ROOT/BRIEF):raise ValueError('authority brief mismatch')
        if not REQUIRED<=set(a.get('source_files',{})):raise ValueError('complete executable source pins required')
        for name,digest in a['source_files'].items():
            f=(ROOT/name).resolve()
            if not f.is_relative_to(ROOT) or sha(f)!=digest:raise ValueError('source pin mismatch')
        for k in ['allocated_gpu_seconds','previous_gpu_seconds','deadline_epoch','provider_created_epoch','packed_science_seconds','setup_allowance_seconds']:
            if not isinstance(a.get(k),(int,float)) or not math.isfinite(a[k]):raise ValueError('finite timing fields required')
        self.initial_allocation=float(a['allocated_gpu_seconds'])
        # Reserve up to the registered ceiling; actual admission comes from this process's
        # retained next-three real timings. Until a path is measured, use F=0 for that path.
        # Thus the provisional cap is always <= min(1.5*full_F+360, ceiling), even mid-pack.
        self.allocation=min(self.initial_allocation,360.)
        if a['previous_gpu_seconds']!=0:raise ValueError('fresh attempt only; no partial reruns')
        if not 180<self.initial_allocation<=CAPS[experiment]:raise ValueError('science reservation cap exceeded')
        if not 0<a['setup_allowance_seconds']<=2400:raise ValueError('shared setup cap exceeded')
        if not 0<a['packed_science_seconds']<=sum(CAPS.values()):raise ValueError('packed science total invalid')
        if not a['provider_created_epoch']<=time.time():raise ValueError('provider clock invalid')
        if a['deadline_epoch']>min(STOP,a['provider_created_epoch']+a['setup_allowance_seconds']+a['packed_science_seconds']):raise ValueError('hardstop exceeds programme or packed budget')
        if time.time()>=a['deadline_epoch']-180:raise TimeoutError('expired assignment')
        self.forecasts={}
        self.expected={'generation','ar'} if experiment=='E1b' else {'olens_native','olens_context','nla_native','nla_context'}
        if a.get('forecast_method')!='warmed_median_next_3_real_units':raise ValueError('median next-three method required')
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')

    def setup_guard(self):
        if self.started is not None:return self.guard()
        self.setup_callback()
        if time.time()>=min(STOP,self.assignment['deadline_epoch'])-180:raise TimeoutError('setup hardstop')

    def start(self):
        if self.started is None:self.setup_guard();self.started=time.monotonic();self.first_science_epoch=time.time()
        self.write_state()
        self.guard()

    def write_state(self):
        if getattr(self,'state_path',None) is not None:
            temporary=self.state_path.with_suffix('.tmp')
            dump(temporary,{'experiment':self.experiment,'first_science_epoch':getattr(self,'first_science_epoch',None),
                'science_cap_seconds':self.allocation,'reserved_ceiling_seconds':self.initial_allocation,
                'status':getattr(self,'state_status','RUNNING'),
                'measured_path_forecasts':self.forecasts,'unmeasured_paths':sorted(self.expected-set(self.phases)),
                'science_clock_resets':0,'retrieval_reserve_seconds':180})
            os.replace(temporary,self.state_path)

    def guard(self):
        if self.started is None:return self.setup_guard()
        if time.monotonic()-self.started>=self.allocation-180 or time.time()>=min(STOP,self.assignment['deadline_epoch'])-180:raise TimeoutError('science cap or retrieval reserve reached')

    def measured(self,name,timings,n,completed):
        if name not in self.expected or name in self.phases:raise ValueError('unknown or repeated timing path')
        if len(timings)!=3 or any(not math.isfinite(t) or t<=0 for t in timings):raise ValueError('three positive warmed real timings required')
        median=statistics.median(timings);self.forecasts[name]=median*n
        self.phases[name]={'timed_unit_seconds':timings,'median_seconds':median,'units':n,'forecast_seconds':median*n,'warmup_scored':False}
        self.allocation=min(self.initial_allocation,1.5*sum(self.forecasts.values())+360,CAPS[self.experiment]);self.write_state()
        remaining=self.forecasts[name]*(n-completed)/n
        if time.monotonic()-self.started+1.5*remaining+180>self.allocation:raise TimeoutError('NO_FIT: remaining measured path exceeds experiment cap')


def collect(units,fn,gate,name,out):
    """All model loading and discarded warm-up happen in the resident process before this."""
    out.mkdir(exist_ok=False,parents=True)
    if len(units)<3:raise ValueError('three retained timing units required')
    gate.start();values=[];timings=[]
    for i,unit in enumerate(units):
        gate.guard();t=time.monotonic();value=fn(unit);dt=time.monotonic()-t
        values.append(value)
        # Retain recoverable partial outputs; incomplete collections cannot be analysed or resumed.
        dump(out/f'unit-{i:05d}.json',value)
        if i<3:timings.append(dt)
        if i==2:
            gate.measured(name,timings,len(units),3);dump(out/'WARMED_FORECAST.json',gate.phases[name])
        gate.guard()
    gate.phases[name]['complete']=True
    seal(out,[p.name for p in out.iterdir() if p.is_file()],'FOLLOWUP_PHASE_COMPLETE_BEFORE_LABEL_JOIN')
    return [row for value in values for row in value]
