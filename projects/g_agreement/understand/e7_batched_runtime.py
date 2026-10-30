"""§94 operational retry: same-process four-phase timing and coordinator's conditional cap."""
import math
import os
import statistics
import time
from .cpu import ROOT,read,dump,sha

BRIEF='projects/g_agreement/BRIEF_UNDERSTAND.md'
STOP=__import__('datetime').datetime(2026,10,28,22,59,tzinfo=__import__('datetime').timezone.utc).timestamp()
PRIOR_SCIENCE=40.436461039993446
PHASES=('readouts','prepare','decoder','scores')


def budget(forecast,previous,reserved):
    ceiling=7200. if forecast>2880. else 2880.
    cumulative=min(1.5*forecast+360,ceiling)
    return ceiling,cumulative,min(reserved,cumulative-previous)


class Gate:
    def __init__(self,path,counts):
        a=read(path);self.assignment=a;self.experiment='E7';self.started=None;self.setup_complete=False
        self.counts=counts;self.samples={k:[] for k in PHASES};self.completed={k:0 for k in PHASES};self.movements={};self.state_status='SETUP'
        if a.get('issuer')!='integrator' or a.get('experiment')!='E7' or a.get('gpu_count')!=1 or not a.get('pod_id'):raise ValueError('exact integrator E7 one-pod assignment required')
        for key in ['external_hardstop_verified','hold_renewer_verified','brief_registered','brief_pushed','conditional_7200_ruling_recorded']:
            if a.get(key) is not True:raise ValueError('missing evidence: '+key)
        if a.get('brief_sha256')!=sha(ROOT/BRIEF):raise ValueError('dated §94 brief mismatch')
        required={'projects/g_agreement/understand/'+n+'.py' for n in ['e7_batched','e7_batched_runtime','e7_parity','e7_solo','worker','packed','analyse','cpu']}
        if not required<=set(a.get('source_files',{})):raise ValueError('complete E7 source pins required')
        for name,digest in a['source_files'].items():
            p=(ROOT/name).resolve()
            if not p.is_relative_to(ROOT) or sha(p)!=digest:raise ValueError('source pin mismatch')
        for key in ['allocated_gpu_seconds','previous_gpu_seconds','provider_created_epoch','setup_deadline_epoch','deadline_epoch','setup_allowance_seconds']:
            if not isinstance(a.get(key),(int,float)) or not math.isfinite(a[key]):raise ValueError('finite timing fields required')
        self.previous=float(a['previous_gpu_seconds']);self.reserved=float(a['allocated_gpu_seconds'])
        if self.previous<PRIOR_SCIENCE or not 180<self.reserved<=7200-self.previous:raise ValueError('prior science or cumulative reservation invalid')
        if not 0<a['setup_allowance_seconds']<=2400 or a['provider_created_epoch']>time.time():raise ValueError('setup/provider timestamp invalid')
        if a['setup_deadline_epoch']>a['provider_created_epoch']+a['setup_allowance_seconds']:raise ValueError('setup deadline exceeds 2400s')
        if a['deadline_epoch']>min(STOP,a['provider_created_epoch']+a['setup_allowance_seconds']+self.reserved):raise ValueError('absolute hardstop exceeds assignment/programme')
        if a.get('forecast_method')!='four_phase_warmed_median_next_3_retained_units':raise ValueError('full four-phase median method required')
        if time.time()>=a['setup_deadline_epoch'] or time.time()>=a['deadline_epoch']-180:raise TimeoutError('expired assignment')
        self.allocation=budget(0,self.previous,self.reserved)[2]
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')

    def setup_guard(self):
        if self.started is not None:return self.guard()
        self.setup_callback()
        if time.time()>=self.assignment['setup_deadline_epoch']:raise TimeoutError('setup exhausted')

    def start(self):
        if self.started is None:
            self.setup_guard();self.started=time.monotonic();self.first_science_epoch=time.time();self.state_status='RUNNING'
        self.write_state();self.guard()

    def forecast(self):
        phase={}
        for key in PHASES:
            samples=self.samples[key];median=statistics.median(samples) if len(samples)==3 else None
            move=2*self.movements.get(key,0.)
            phase[key]={'timed_unit_seconds':samples,'units':self.counts[key],'completed_units':self.completed[key],
                'median_seconds':median,'unit_forecast_seconds':None if median is None else median*self.counts[key],
                'residency_transfer_forecast_seconds':move,'forecast_seconds':None if median is None else median*self.counts[key]+move}
        total=sum(v['forecast_seconds'] or 0. for v in phase.values());ceiling,cumulative,allocation=budget(total,self.previous,self.reserved)
        return {'phases':phase,'F_seconds':total,'all_four_phases_measured':all(len(v)==3 for v in self.samples.values()),
            'selected_ceiling_seconds':ceiling,'coordinator_extension_used':ceiling==7200,'cumulative_cap_seconds':cumulative,
            'previous_science_seconds':self.previous,'new_attempt_cap_seconds':allocation,'science_clock_resets':0,
            'first_science_epoch':getattr(self,'first_science_epoch',None),'elapsed_science_seconds':0 if self.started is None else time.monotonic()-self.started,
            'forecast_scope':'all units of all four phases; two measured decoder/NLA round trips including pilot and completion; setup checkpoint loads excluded',
            'unmeasured_phase_contribution':'0 until own first3 retained units; provisional cap is conservative lower bound'}

    def write_state(self):
        if not hasattr(self,'out'):return
        report=self.forecast();self.allocation=report['new_attempt_cap_seconds']
        report.update(status=self.state_status,retrieval_reserve_seconds=180)
        temp=self.out/'CLOCK.tmp';dump(temp,report);os.replace(temp,self.out/'CLOCK.json')

    def guard(self):
        if self.started is None:return self.setup_guard()
        if time.monotonic()-self.started>=self.allocation-180 or time.time()>=min(STOP,self.assignment['deadline_epoch'])-180:raise TimeoutError('E7 science/retrieval deadline reached')

    def record(self,key,elapsed):
        if not math.isfinite(elapsed) or elapsed<=0:raise ValueError('finite positive warmed unit timing required')
        self.completed[key]+=1
        if len(self.samples[key])<3:self.samples[key].append(elapsed)
        self.write_state();self.guard()

    def movement(self,key,elapsed):
        if key not in ['decoder','scores'] or key in self.movements or not math.isfinite(elapsed) or elapsed<=0:raise ValueError('single measured residency transition required')
        self.movements[key]=elapsed;self.write_state();self.guard()

    def admit_remaining(self):
        report=self.forecast()
        if not report['all_four_phases_measured'] or set(self.movements)!={'decoder','scores'}:raise ValueError('all four warmed phase forecasts and both residency transfers required')
        remaining=sum(v['median_seconds']*(v['units']-v['completed_units']) for v in report['phases'].values())+sum(self.movements.values())
        report.update(remaining_forecast_seconds=remaining,retrieval_reserve_seconds=180,
            fit=report['elapsed_science_seconds']+remaining+180<=self.allocation)
        dump(self.out/'FULL_WARMED_FORECAST.json',report)
        dump(self.out/'FORECAST_SEAL.json',{'status':'E7_FULL_FOUR_PHASE_FORECAST_SEALED_BEFORE_REMAINING_ADMISSION',
            'files':{'FULL_WARMED_FORECAST.json':sha(self.out/'FULL_WARMED_FORECAST.json')}})
        if not report['fit']:raise TimeoutError('NO_FIT: full four-phase batched forecast exceeds selected cap')
        self.guard();return report
