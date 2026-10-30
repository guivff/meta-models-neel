"""E40 one-pod wall clock; full50400-second experiment cap incl all custody."""
import math
import os
import re
import statistics
import time
from datetime import datetime,timezone
TOTAL=79000
RESERVE=180
LATER=0
STOP=datetime(2026,10,28,22,59,tzinfo=timezone.utc).timestamp()
class NoFit(TimeoutError):pass

def number(x):return type(x)in(int,float)and math.isfinite(x)

class Clock:
    def __init__(self,a,request_sha,now=None):
        now=time.time()if now is None else now
        if (a.get('issuer')!='integrator' or a.get('experiment')!='E40'
                or a.get('stage')!='training' or type(a.get('gpu_count'))is not int or a['gpu_count']!=1
                or a.get('request_sha256')!=request_sha or not re.fullmatch('[0-9a-f]{64}',request_sha)
                or not re.fullmatch('[0-9a-f]{40}',a.get('source_commit',''))
                or not a.get('pod_id')or os.environ.get('RUNPOD_POD_ID')!=a['pod_id']):
            raise ValueError('exact published single-pod Integrator assignment required')
        if any(a.get(k)is not True for k in('source_pushed','external_hardstop_verified','hold_renewer_verified')):
            raise ValueError('push,hardstop,hold evidence required')
        for k in('provider_created_epoch','deadline_epoch','setup_deadline_epoch',
                 'previous_gpu_seconds','allocated_gpu_seconds','later_reserved_gpu_seconds'):
            if not number(a.get(k)):raise ValueError('finite custody timing required')
        previous,allocated,later=a['previous_gpu_seconds'],a['allocated_gpu_seconds'],a['later_reserved_gpu_seconds']
        start,deadline,setup=a['provider_created_epoch'],a['deadline_epoch'],a['setup_deadline_epoch']
        if (previous<0 or not RESERVE<allocated<=TOTAL-LATER or later<LATER
                or previous+allocated+later>TOTAL or not start<=now<setup<=min(start+1500,deadline-RESERVE)
                or not setup<deadline<=min(start+allocated,STOP)):
            raise ValueError('E40 total,stage,setup or programme budget invalid')
        self.a=dict(a);self.science_start=None;self.science_limit=None;self.forecast=None;self.status='SETUP'
        self.forecast_components=None
    def check(self):
        limit=self.a['deadline_epoch']-RESERVE
        if self.science_start is None:limit=min(limit,self.a['setup_deadline_epoch'])
        elif self.science_limit is not None:limit=min(limit,self.science_start+self.science_limit)
        if self.status=='NO_FIT'or time.time()>=limit:
            self.status='NO_FIT';raise NoFit('E40 timing cap; no scope reduction')
    def begin(self):
        self.check()
        if self.science_start is not None:raise ValueError('science clock cannot reset')
        self.science_start=time.time();self.status='CALIBRATION'
    def admit(self,*,calibration_elapsed,calibration_chunks,calibration_retained,
              full_chunk_seconds,optimizer_seconds,evaluation_seconds):
        self.check()
        if self.science_start is None or self.forecast is not None:raise ValueError('single admission required')
        if (not number(calibration_elapsed)or calibration_elapsed<=0 or type(calibration_chunks)is not int
                or calibration_chunks<1 or type(calibration_retained)is not int or not 0<calibration_retained<=1000000):
            raise ValueError('complete fixed calibration and positive retained count required')
        for timings in(full_chunk_seconds,optimizer_seconds,evaluation_seconds):
            if len(timings)!=3 or any(not number(t)or t<=0 for t in timings):
                raise ValueError('three complete warmed timings per path required')
        per_chunk=max(statistics.median(full_chunk_seconds),calibration_elapsed/calibration_chunks)
        remaining_chunks=math.ceil((100000000-calibration_retained)*calibration_chunks/calibration_retained)
        steps=math.ceil(100000000/4096)
        elapsed=time.time()-self.science_start
        components={'elapsed_before_training':elapsed,'capture_filter_seconds':remaining_chunks*per_chunk,
                    'optimizer_seconds':steps*statistics.median(optimizer_seconds),
                    'gate_seconds':math.ceil(50000/256)*statistics.median(evaluation_seconds),
                    'remaining_capture_chunks_forecast':remaining_chunks,'optimizer_steps':steps,
                    'calibration_retained':calibration_retained}
        self.forecast=sum(components[k]for k in('elapsed_before_training','capture_filter_seconds','optimizer_seconds','gate_seconds'))
        self.forecast_components=components
        self.science_limit=min(1.5*self.forecast+360,self.a['deadline_epoch']-RESERVE-self.science_start)
        if self.forecast+180>self.science_limit:
            self.status='NO_FIT';raise NoFit('full100M training and unchanged gate do not fit')
        self.status='TRAINING'
    def record(self):
        return {'status':self.status,'first_science_epoch':self.science_start,'science_clock_resets':0,
                'forecast_seconds':self.forecast,'forecast_components':self.forecast_components,
                'science_cap_seconds':self.science_limit,
                'provider_elapsed_seconds':time.time()-self.a['provider_created_epoch'],
                'previous_gpu_seconds':self.a['previous_gpu_seconds'],
                'later_reserved_gpu_seconds':self.a['later_reserved_gpu_seconds'],'retrieval_reserve_seconds':RESERVE}
