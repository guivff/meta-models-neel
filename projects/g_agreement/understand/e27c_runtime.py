"""E27(c) §133 item6: one fresh allocation, including setup/retrieval, <=2 GPU-h."""
import math
import os
import statistics
import time
from datetime import datetime,timezone
from .cpu import ROOT,read,dump,sha
from .e27c import PUBLIC

PATHS=('ol_generation','nla_generation','reconstruction','asked')
TOTAL_SECONDS=7200
REQUEST=PUBLIC/'retry_17472735'
RESERVE=180
STOP=datetime(2026,10,28,22,59,tzinfo=timezone.utc).timestamp()


class NoFit(TimeoutError):pass


class Gate:
    def __init__(self,path,counts):
        self.a=read(path);self.assignment_sha=sha(path);self.counts=counts
        self.started=None;self.samples={k:[] for k in PATHS};self.warms={};self.admitted=False
        self.cap=None;self.status='SETUP';self.completed={k:0 for k in PATHS}
        a=self.a
        if a.get('issuer')!='integrator' or a.get('experiment')!='E27C' or a.get('gpu_count')!=1 or not a.get('pod_id'):
            raise ValueError('exact integrator E27C single GPU assignment required')
        if a.get('attempt')!=2 or a.get('authority_commit')!='17472735' or a['pod_id']=='2a3pwvf3e7vxf5':
            raise ValueError('one fresh section133 item6 attempt2 required')
        if a.get('head_warning_reviewed') is not True or a.get('head_review_sha256')!=sha(REQUEST/'HEAD_REVIEW.json'):
            raise ValueError('completed pinned head review required')
        if read(REQUEST/'HEAD_REVIEW.json')['status']!='BENIGN_DISCARDED_MODULES_VERIFIED':
            raise ValueError('head warning must be resolved before setup')
        for k in ('brief_pushed','external_hardstop_verified','hold_renewer_verified','E23_analysis_posted','E26_analysis_posted'):
            if a.get(k) is not True:raise ValueError(k+' required')
        for k in ('provider_created_epoch','deadline_epoch','setup_deadline_epoch'):
            if not isinstance(a.get(k),(int,float)) or not math.isfinite(a[k]):raise ValueError(k+' required')
        if not a['provider_created_epoch']<=time.time()<a['setup_deadline_epoch']<a['deadline_epoch']:raise ValueError('invalid absolute setup times')
        if a['deadline_epoch']>min(STOP,a['provider_created_epoch']+TOTAL_SECONDS):raise ValueError('total setup+science exceeds 2.0 GPU-h')
        if a['setup_deadline_epoch']>min(a['deadline_epoch']-RESERVE,a['provider_created_epoch']+1500):raise ValueError('setup allowance exceeds 1500s or total budget')
        for key,name in [('plan_sha256','PLAN.json'),('brief_sha256','BRIEF_UNDERSTAND.authority.md')]:
            if a.get(key)!=sha(REQUEST/name):raise ValueError('plan/authority mismatch')
        required={'projects/g_agreement/understand/'+n+'.py' for n in ('e27c','e27c_runtime','e27c_worker','e27c_analyse','cpu')}
        if not required<=a.get('source_files',{}).keys():raise ValueError('source manifest incomplete')
        for name,digest in a['source_files'].items():
            p=(ROOT/name).resolve()
            if not p.is_relative_to(ROOT.resolve()) or sha(p)!=digest:raise ValueError('source pin mismatch')
        if set(counts)!=set(PATHS) or any(n<=0 for n in counts.values()):raise ValueError('complete full-run path counts required')
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')
        self.setup_guard()

    def setup_guard(self):
        if time.time()>=self.a['setup_deadline_epoch']:raise NoFit('setup deadline reached')
        self.guard_total()

    def guard_total(self):
        if time.time()>=self.a['deadline_epoch']-RESERVE:raise NoFit('total GPU allocation retrieval reserve reached')

    def elapsed(self):return 0. if self.started is None else time.monotonic()-self.started

    def state(self):
        return {'status':self.status,'science_seconds':self.elapsed(),'science_cap_seconds':self.cap,
                'first_science_epoch':getattr(self,'first_epoch',None),'deadline_epoch':self.a['deadline_epoch'],
                'total_GPU_limit_seconds':TOTAL_SECONDS,'setup_included':True,'retrieval_reserve_seconds':RESERVE,
                'science_clock_resets':0,'bulk_admitted':self.admitted,'counts':self.counts,
                'completed':self.completed,'samples':self.samples,'warmups':self.warms}

    def write(self):
        if not hasattr(self,'out'):return
        p=self.out/'CLOCK.tmp';dump(p,self.state());os.replace(p,self.out/'CLOCK.json')

    def guard(self):
        self.guard_total()
        if self.started is None:self.setup_guard()
        elif self.cap is not None and self.elapsed()>=self.cap-RESERVE:raise NoFit('science forecast cap retrieval reserve reached')

    def warm(self,key,seconds):
        self.setup_guard()
        if self.started is not None or key not in PATHS or key in self.warms or seconds<=0 or not math.isfinite(seconds):raise ValueError('single setup warm-up required')
        self.warms[key]=seconds;self.write()

    def start(self):
        self.setup_guard()
        if self.started is not None or set(self.warms)!=set(PATHS):raise ValueError('one start after all warmed paths')
        self.started=time.monotonic();self.first_epoch=time.time();self.status='PILOT';self.write()

    def record(self,key,seconds,retained):
        if self.started is None or key not in PATHS or seconds<=0 or not math.isfinite(seconds):raise ValueError('finite timed science required')
        if retained:
            if not self.admitted or self.completed[key]>=self.counts[key]:raise ValueError('production outside admission or duplicate unit')
            self.completed[key]+=1
        else:
            if self.admitted or len(self.samples[key])>=3:raise ValueError('exactly three discarded timing units per path')
            self.samples[key].append(seconds)
        self.write();self.guard()

    def admit(self,movement_seconds):
        if self.admitted or self.status!='PILOT' or any(len(v)!=3 for v in self.samples.values()):raise ValueError('all four full warmed paths required')
        if not math.isfinite(movement_seconds) or movement_seconds<=0:raise ValueError('measured model movement bound required')
        # Each phase change is bounded by twice the slowest measured move including offload.
        remaining=sum(self.counts[k]*statistics.median(self.samples[k]) for k in PATHS)+8*movement_seconds
        F=self.elapsed()+remaining
        self.cap=min(1.5*F+360,self.a['deadline_epoch']-self.first_epoch)
        report={**self.state(),'F_seconds':F,'remaining_forecast_seconds':remaining,
                'movement_bound_seconds':8*movement_seconds,'formula':'min(1.5F+360,remaining total allocation)',
                'science_cap_seconds':self.cap,'fit':self.elapsed()+remaining+RESERVE<=self.cap,
                'unknown_paths_are_zero':False}
        dump(self.out/'FULL_WARMED_FORECAST.json',report)
        dump(self.out/'FORECAST_SEAL.json',{'status':'E27C_FULL_FORECAST_BEFORE_PRODUCTION',
             'files':{'FULL_WARMED_FORECAST.json':sha(self.out/'FULL_WARMED_FORECAST.json')}})
        if not report['fit']:
            self.status='NO_FIT';self.write();raise NoFit('full E27C run does not fit <=2.0 GPU-h including setup')
        self.admitted=True;self.status='PRODUCTION';self.write();self.guard()
