"""E95 admission-only clock: unpadded setup and measured arm/layer/width work.

The original worker87 capture/native/acquire path and late198 Clock stay unchanged.
Invoke this module with the exact worker87 arguments for the amendment1 relaunch.
"""
import argparse
from collections import Counter
import math
import sys
import time
import numpy as np
import worker87 as W
from worker import Clock,NoFit
import representative95 as R
METHOD="REPRESENTATIVE_PHASE_WIDTH_V3_AMENDMENT1"
MARGIN=1.15
CEILING=194400
AUTHORITY="c579174dc"


def schedule(items,plan):
    from scope95 import pseudo_items
    pseudos=pseudo_items(plan);jobs={'oracle_native':[],'nla_native':[]}
    for reader,layers in [('oracle',plan['layers']),('nla',[42])]:
        for layer in layers:
            for arm,xs in [('real',items),('placebo',pseudos)]:
                if plan['mode']=='nla_placebo_only' and (reader!='nla' or arm!='placebo'):continue
                for x in xs:
                    width=min(8,len(x['ids']) if 'ids' in x else x['position_count'])
                    jobs[reader+'_native'].append(f'{reader}:{arm}:{layer}:{width}')
    W.require(dict(Counter(k for v in jobs.values() for k in v))==R.aggregate_workload(items,plan),
              'exact unchanged native phase/arm/layer/width grid')
    return jobs


def forecast(remaining,seed,observed,native_remaining,native_rates,native_observed,warmups):
    """All remaining work gets1.15; setup and discarded warm-ups do not."""
    rates={}
    for k,n in native_remaining.items():
        if n:rates[k]=max(native_rates[k],float(np.mean(native_observed[k]))) if native_observed.get(k) else native_rates[k]
    work=sum(n*rates[k] for k,n in native_remaining.items() if n)
    general={}
    for phase in ('capture','placebo_build'):
        if remaining.get(phase,0):
            general[phase]=float(np.mean(observed[phase])) if observed.get(phase) else seed[phase]
            work+=remaining[phase]*general[phase]
    setup=sum(remaining[p]*seed[p] for p in ('oracle_setup','nla_setup') if remaining.get(p,0))+sum(warmups.values())
    values=list(rates.values())+list(general.values())+[setup,work]
    W.require(all(math.isfinite(x) and x>=0 for x in values),'finite measured remaining forecast')
    return dict(remaining_setup_seconds=setup,remaining_work_seconds=work,
        remaining_forecast_seconds=setup+MARGIN*work,margin=MARGIN,
        native_remaining=dict(native_remaining),native_seconds_per_batch=rates,
        general_seconds_per_batch=general,unobserved_warmups_seconds=warmups)


class AdmissionClock95(Clock):
    def __init__(self,out,end,seeds,backend,items,plan,measured):
        super().__init__(out,end,seeds,backend)
        W.require(measured['method']==METHOD,'representative measured admission only')
        self.plan=plan;self.book=measured['rate_book'];self.jobs=schedule(items,plan)
        self.cursor={k:0 for k in self.jobs};self.left=Counter(k for xs in self.jobs.values() for k in xs)
        self.native_observed={}
    def call(self,phase,fn,real=False):
        key=None
        if real and phase in self.jobs:
            i=self.cursor[phase];W.require(i<len(self.jobs[phase]),'no extra native jobs')
            key=self.jobs[phase][i]
        result=super().call(phase,fn,real=real)
        if key is not None:
            self.native_observed.setdefault(key,[]).append(self.events[-1]['seconds'])
            self.left[key]-=1;self.cursor[phase]+=1
            self.events[-1]['native_stratum']=key
            W.write(self.out/'PHASE_TIMINGS.json',self.events,replace=True)
        return result
    def snapshot(self,now):
        for phase in self.jobs:
            W.require(self.remaining.get(phase,0)==len(self.jobs[phase])-self.cursor[phase],
                      'remaining native counters align with original worker')
        done={e['phase'] for e in self.events if e['status']=='COMPLETE'}
        names=['nla_42_warmup_discarded']
        if self.plan['mode']=='remaining':names+=['capture_warmup_discarded']+[f'oracle_{l}_warmup_discarded' for l in self.plan['layers']]
        warmups={k:self.book['other'][k] for k in names if k not in done}
        f=forecast(self.remaining,self.seeds,self.observed,self.left,self.book['native'],self.native_observed,warmups)
        f.update(estimator='section217 unpadded remaining setup/warmups +1.15work; native running means only within frozen arm/layer/width stratum',
                 status='ADMIT' if now+f['remaining_forecast_seconds']<self.end-60 else 'NO_FIT',
                 now_epoch=now,deadline_epoch=self.end,retrieval_reserve_seconds=60,
                 remaining=self.remaining,maximum_measured_setup_seconds=self.book['maximum_measured_setup_seconds'],
                 original_creation_clock_unchanged=True,warmups_excluded_from_work_rates=True)
        return f
    def admit(self):
        self.check();value=self.snapshot(time.time());W.write(self.out/'FORECAST.json',value,replace=True)
        if value['status']!='ADMIT':raise NoFit('remaining section217 setup/work forecast does not fit fixed cap')


def validate_production(assignment,limits,plan,inp,source_sha):
    W.require(getattr(W,'_admission95_active',False),'amendment1 requires admission95.py entrypoint (live1.15 clock)')
    m=limits['timing95'];W.require(m['method']==METHOD and m['amendment_authority']==AUTHORITY and m['margin']==MARGIN,
                                'registered amendment1 work margin')
    W.require(m['ceiling_seconds']==CEILING and
        0<=m['prior_custody_seconds']<=m['programme_projected_custody_seconds']<=CEILING,
        'amendment1 cumulative original custody')
    W.require(m['source_seal_sha256']==source_sha and m['plan_sha256']==W.sha(inp/'PLAN.json') and
        m['items_sha256']==W.sha(inp/'items.json') and m['row_indices']==plan['row_indices'] and
        m['reduction_step']==plan['reduction_step']==3,'same frozen source and whole-row scope')
    f=R.estimate(W.read(inp/'items.json'),plan,m['rate_book'],margin=MARGIN)
    W.require(f==m['forecast'] and not f['missing_native_phases'] and
        limits['cap_seconds']==m['cap_seconds']==f['cap_seconds'],'repriced setup +1.15work cap arithmetic')
    W.require(m['profile_set_sha256']==m['rate_book']['profile_set_sha256']==
        R.digest(sorted(m['rate_book']['evidence'],key=lambda x:x['profile_sha256'])),'repricing evidence identity')
    W.require(assignment['pod_created_epoch']==assignment['custody_start_epoch'],'original creation clock required')
    for k in ['gpu_type','image_digest','stack_sha256','assets_sha256','scope_seal_sha256','inventory_sha256','index_sha256']:
        W.require(assignment[k]==m[k],'amendment1 assignment '+k)
        if k in m['rate_book']['hardware']:W.require(m[k]==m['rate_book']['hardware'][k],'same measured runtime '+k)
    from contract import digest
    W.require(assignment['measured_profile_set_sha256']==m['profile_set_sha256'] and
        assignment['measured_decision_sha256']==m['measured_decision_sha256'] and
        digest(assignment['e95_integrator_admission_sha256']),'fresh independent I3 admission')


def main():
    if '--help' in sys.argv or '-h' in sys.argv:return W.main()
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--inputs',required=True,type=__import__('pathlib').Path)
    a,_=p.parse_known_args();items=W.read(a.inputs/'items.json');plan=W.read(a.inputs/'PLAN.json');limits=W.read(a.inputs/'STAGE_REQUEST.json')
    W.require(plan['experiment']=='E95','E95-only admission wrapper')
    original=W.Clock
    W._admission95_active=True
    W.Clock=lambda out,end,seeds,b:AdmissionClock95(out,end,seeds,b,items,plan,limits['timing95'])
    try:return W.main()
    finally:
        W.Clock=original;W._admission95_active=False

if __name__=='__main__':main()
