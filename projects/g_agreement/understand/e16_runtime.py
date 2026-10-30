"""Bounded E16 pilot: every path measured, no unknown-path zero forecast or clock reset."""
import math,os,statistics,time
from .cpu import ROOT,read,dump,sha

BRIEF='results/g_agreement/understand/e16/BRIEF_UNDERSTAND.1095e4e9.md'
PATHS=('olens_dev','olens_test','base_dev','base_test','nla_dev','nla_test',
       'olens_greedy','olens_sampled','nla_greedy','nla_sampled')
STOP=__import__('datetime').datetime(2026,10,28,22,59,tzinfo=__import__('datetime').timezone.utc).timestamp()


class NoFit(TimeoutError):pass


class Gate:
    def __init__(self,path,counts):
        a=read(path);self.assignment=a;self.assignment_sha256=sha(path);self.counts=counts;self.started=None;self.first_science_epoch=None
        self.samples={k:[] for k in PATHS};self.completed={k:0 for k in PATHS};self.warmups={};self.movements={}
        self.discarded_timing_seconds=0.;self.cap=None;self.admitted=False;self.status='SETUP'
        if set(counts)!=set(PATHS) or any(type(n) is not int or n<3 for n in counts.values()):raise ValueError('all ten frozen timing paths required')
        if a.get('issuer')!='integrator' or a.get('experiment')!='E16' or a.get('gpu_count')!=1 or not a.get('pod_id'):raise ValueError('exact integrator one-pod E16 assignment required')
        for k in ['brief_registered','brief_pushed','external_hardstop_verified','hold_renewer_verified']:
            if a.get(k) is not True:raise ValueError(k+' evidence required')
        if a.get('brief_sha256')!=sha(ROOT/BRIEF):raise ValueError('authority brief mismatch')
        required={'projects/g_agreement/understand/'+n+'.py' for n in ['e16','e16_worker','e16_runtime','e16_analyse','cpu','e12']}
        if not required<=set(a.get('source_files',{})):raise ValueError('complete source pins required')
        for f,d in a['source_files'].items():
            p=(ROOT/f).resolve()
            if not p.is_relative_to(ROOT) or sha(p)!=d:raise ValueError('source pin mismatch')
        for k in ['allocated_gpu_seconds','previous_gpu_seconds','provider_created_epoch','setup_deadline_epoch','deadline_epoch','setup_allowance_seconds']:
            if not isinstance(a.get(k),(int,float)) or not math.isfinite(a[k]):raise ValueError('finite timing fields required')
        self.reserved=float(a['allocated_gpu_seconds'])
        if not 180<self.reserved<=2400 or a['previous_gpu_seconds']!=0:raise ValueError('fresh E16 science cap <=2400 required')
        if not 0<a['setup_allowance_seconds']<=2400 or a['provider_created_epoch']>time.time():raise ValueError('setup/provider invalid')
        if a['setup_deadline_epoch']>a['provider_created_epoch']+a['setup_allowance_seconds']:raise ValueError('setup exceeds2400')
        if a['deadline_epoch']>min(STOP,a['provider_created_epoch']+a['setup_allowance_seconds']+self.reserved):raise ValueError('absolute/programme deadline exceeded')
        if a.get('forecast_method')!='all_ten_paths_warmed_median3_before_bulk':raise ValueError('full warmed forecast required')
        self.setup_guard();os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')

    def setup_guard(self):
        if self.started is not None:return self.guard()
        if time.time()>=min(self.assignment['setup_deadline_epoch'],self.assignment['deadline_epoch']-180,STOP-180):raise TimeoutError('setup/absolute deadline reached')

    def start(self):
        if self.started is None:
            self.setup_guard()
            if set(self.warmups)!=set(PATHS):raise ValueError('every path needs one unscored warm-up')
            self.started=time.monotonic();self.first_science_epoch=time.time();self.status='RUNNING'
        self.write_state();self.guard()

    def elapsed(self):return 0. if self.started is None else time.monotonic()-self.started

    def forecast(self):
        paths={k:{'units':self.counts[k],'completed_units':self.completed[k],'timed_unit_seconds':self.samples[k],
            'median_seconds':statistics.median(self.samples[k]) if len(self.samples[k])==3 else None,'warmup':self.warmups.get(k)} for k in PATHS}
        for v in paths.values():v['forecast_seconds']=None if v['median_seconds'] is None else v['median_seconds']*v['units']
        full=all(v['median_seconds'] is not None for v in paths.values()) and 'roundtrip_half' in self.movements
        F=sum(v['forecast_seconds'] for v in paths.values())+self.discarded_timing_seconds+2*self.movements['roundtrip_half'] if full else None
        cap=min(self.reserved,1.5*F+360,2400) if full else None
        return {'paths':paths,'all_paths_measured':full,'F_seconds':F,'formula_cap_seconds':cap,
            'science_cap_seconds':self.cap if self.cap is not None else self.reserved,
            'reserved_pilot_only':self.cap is None,'bulk_admitted':self.admitted,'status':self.status,
            'first_science_epoch':self.first_science_epoch,'elapsed_science_seconds':self.elapsed(),
            'science_clock_resets':0,'discarded_test_path_timing_science_seconds':self.discarded_timing_seconds,
            'transfer_forecast_seconds':None if not self.movements else 2*self.movements['roundtrip_half'],
            'retrieval_reserve_seconds':180,'unknown_paths_are_zero':False}

    def write_state(self):
        if not hasattr(self,'out'):return
        t=self.out/'CLOCK.tmp';dump(t,self.forecast());os.replace(t,self.out/'CLOCK.json')

    def guard(self):
        if self.started is None:return self.setup_guard()
        limit=self.reserved if self.cap is None else self.cap
        if self.elapsed()>=limit-180 or time.time()>=min(STOP,self.assignment['deadline_epoch'])-180:raise TimeoutError('science/retrieval deadline reached')

    def warm(self,k,seconds):
        self.setup_guard()
        if self.started is not None or k not in PATHS or k in self.warmups or seconds<=0 or not math.isfinite(seconds):raise ValueError('one finite setup warm-up per path required')
        self.warmups[k]={'seconds':seconds,'scored':False};self.write_state()

    def record(self,k,seconds,retained=True):
        if not math.isfinite(seconds) or seconds<=0:raise ValueError('positive unit timing required')
        if not self.admitted and len(self.samples[k])>=3:raise ValueError('bulk blocked until all paths timed')
        if not retained:
            if not k.endswith('_test') or self.admitted:raise ValueError('only dev-sourced test-path timing probes may be discarded')
            self.discarded_timing_seconds+=seconds
        else:self.completed[k]+=1
        if len(self.samples[k])<3:self.samples[k].append(seconds)
        self.write_state();self.guard()

    def movement(self,seconds):
        if self.movements or not math.isfinite(seconds) or seconds<=0:raise ValueError('one measured residency half-roundtrip required')
        self.movements['roundtrip_half']=seconds;self.write_state();self.guard()

    def admit(self):
        r=self.forecast()
        if not r['all_paths_measured']:raise ValueError('all ten paths and residency timing required before admission')
        self.cap=r['formula_cap_seconds'];remaining=sum(v['median_seconds']*(v['units']-v['completed_units']) for v in r['paths'].values())+self.movements['roundtrip_half']
        r.update(remaining_forecast_seconds=remaining,fit=self.elapsed()+remaining+180<=self.cap)
        dump(self.out/'FULL_WARMED_FORECAST.json',r);dump(self.out/'FORECAST_SEAL.json',{'status':'E16_FULL_TEN_PATH_FORECAST_BEFORE_BULK','files':{'FULL_WARMED_FORECAST.json':sha(self.out/'FULL_WARMED_FORECAST.json')}});self.write_state()
        if not r['fit']:raise NoFit('NO_FIT: full E16 warmed forecast exceeds min(1.5F+360,2400) and retrieval reserve')
        self.guard();self.admitted=True;self.write_state()
