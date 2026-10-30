"""Bounded E95-only measurements through the existing acquire/reader paths."""
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import signal
import threading
import time
import numpy as np
import worker87 as W
from scope95 import pseudo_items
from hardware204 import bind_units,production_gate,validate_e95

AUTHORITY='1b0a2fcfc50d8d57d97a2f3cd84f8f88ca4e4a85'


def key(reader,arm,layer,width):return f'{reader}:{arm}:{layer}:{width}'


def workload(items,plan):
    W.validate(items,plan);W.require(len(plan['row_indices'])==1,'one whole frozen row per timing shard')
    counts=Counter()
    for reader,layers in [('oracle',plan['layers']),('nla',[42])]:
        for arm,xs in [('real',items),('placebo',pseudo_items(plan))]:
            if plan['mode']=='nla_placebo_only' and (reader!='nla' or arm!='placebo'):continue
            for layer in layers:
                for x in xs:
                    width=min(8,len(x['ids'])) if arm=='real' else x['position_count']
                    counts[key(reader,arm,layer,width)]+=1
    return dict(counts)


class ProfileClock(W.Clock):
    profile95=True
    def __init__(self,*args):super().__init__(*args);self.selected=Counter()
    def admit(self):self.check() # Timing has a fixed custody cap, not a science forecast gate.
    def select(self,reader,arm,layer,width):
        k=key(reader,arm,layer,width)
        take=(reader=='nla' and arm=='placebo') or self.selected[k]<3
        if take:self.selected[k]+=1
        return take
    def native(self,reader,arm,layer,h,fn):
        W.require(np.isfinite(h).all(),'finite timing vectors')
        values=self.call(key(reader,arm,layer,len(h)),fn,real=True)
        for v in values:json.dumps(v,allow_nan=False)
        return values


def measure(inp,items,plan,b,out,binding,end,staging_seconds):
    full=workload(items,plan);clock=ProfileClock(out,end,{},b);started=time.monotonic()
    W.acquire(inp,items,plan,b,clock,out,dict(binding,timing_only=True,scientific_use_allowed=False))
    elapsed=time.monotonic()-started
    native={k:dict(measured_batches=len(clock.observed[k]),mean_seconds=float(np.mean(clock.observed[k])),
        full_batches=n) for k,n in full.items()}
    W.require(all(v['measured_batches']==v['full_batches'] for k,v in native.items() if k.startswith('nla:placebo:')),
        'all fifteen matched NLA placebo pseudo-items timed')
    events_seconds=sum(e['seconds'] for e in clock.events)
    non_native=sum(e['seconds'] for e in clock.events if e['phase'] not in native)
    overhead=max(0,elapsed-events_seconds)
    estimate=staging_seconds+non_native+overhead+sum(v['full_batches']*v['mean_seconds'] for v in native.values())+60
    report=dict(binding,status='E95_TIMING_ONLY_NOT_SCIENCE',native_phases=native,
        phase_timings_sha256=W.sha(out/'PHASE_TIMINGS.json'),plan_sha256=W.sha(inp/'PLAN.json'),
        items_sha256=W.sha(inp/'items.json'),workload=full,margin=1.25,forecast_seconds=math.ceil(estimate*1.25),
        staging_seconds=staging_seconds,non_native_seconds=non_native,measured_other_seconds=overhead,
        profile_seconds=elapsed,all_nla_placebos_timed=True,production_admitted=False,
        regenerate_all_readouts=True,**W.first_output(out))
    W.write(out/'MEASURED_PROFILE.json',report)
    return report


def main():
    p=argparse.ArgumentParser()
    for n in ['inputs','assets','assignment','staging-receipt','out']:p.add_argument('--'+n,type=Path,required=True)
    for n in ['source-sha','input-sha']:p.add_argument('--'+n,required=True)
    p.add_argument('--hardware-receipt',type=Path);p.add_argument('--reuse-hardware',type=Path)
    a=p.parse_args();W.verify(W.HERE,'SOURCE_SEAL.json',a.source_sha)
    for n,h in W.read(W.HERE/'DEPENDENCIES.json').items():W.require(W.sha(W.ROOT/n)==h,'source dependency')
    seal=W.verify(a.inputs,'INPUT_SEAL.json',a.input_sha)
    W.require(set(seal['files'])=={'PLAN.json','items.json','STAGE_REQUEST.json'},'public timing allowlist')
    W.require({x.name for x in a.inputs.iterdir()}==set(seal['files'])|{'INPUT_SEAL.json'},'no extra timing files')
    plan=W.read(a.inputs/'PLAN.json');items=W.validate(W.read(a.inputs/'items.json'),plan);workload(items,plan)
    W.require(not any(x['reuse44'] for x in items),'timing requires own source-bound capture, not unbound reuse44')
    ass=W.read(a.assignment);limits=W.read(a.inputs/'STAGE_REQUEST.json')
    W.require(limits['status']=='READY_E95_TIMING_ONLY' and ass['row_indices']==plan['row_indices'] and ass['shard']==plan['shard'],'timing assignment')
    W.require(ass['custody_start_epoch']==ass['pod_created_epoch'],'creation-bound custody')
    end=W.deadline(ass,limits,time.time())
    for name in ['inventory_sha256','index_sha256','scope_seal_sha256']:
        W.require(ass[name]==limits[name],'frozen CPU scope identity')
    stage=W.read(a.staging_receipt)
    W.require(stage['assignment_sha256']==W.sha(a.assignment) and stage['pod_created_epoch']==ass['pod_created_epoch'] and
        ass['pod_created_epoch']<=stage['worker_ready_epoch']<=time.time()<end-60,'sealed creation-through-staging timing')
    staging=stage['worker_ready_epoch']-ass['pod_created_epoch']
    W.require(staging<=900,'original staging allowance')
    reused=None
    if plan['mode']=='nla_placebo_only':
        W.require(a.reuse_hardware and W.sha(a.reuse_hardware)==ass['reuse_hardware_sha256'],'verified original E87 row hardware')
        reused=W.read(a.reuse_hardware)
    bind_units(ass,plan['row_indices'],reused)
    W.require(ass['assets_sha256']==W.sha(a.assets),'assigned asset manifest identity')
    hardware=production_gate(ass,a.hardware_receipt,a.assets,['oracle','nla'])
    hardware['e95_policy']=validate_e95(ass,plan,reused,a.hardware_receipt,hardware)
    from contract import digest
    W.require(digest(ass['stack_sha256']) and ass['image_digest'].startswith('sha256:') and digest(ass['image_digest'][7:]),'observed immutable image/stack')
    binding=dict(experiment='E95',source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,
        gpu_type=ass['gpu_type'],hardware=hardware,assets_sha256=W.sha(a.assets),row_indices=plan['row_indices'],
        reduction_step=plan['reduction_step'],inventory_sha256=ass['inventory_sha256'],index_sha256=ass['index_sha256'],
        scope_seal_sha256=ass['scope_seal_sha256'],staging_receipt_sha256=W.sha(a.staging_receipt),synthetic=False)
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'ASSIGNMENT.json').write_bytes(a.assignment.read_bytes());(a.out/'STAGING_RECEIPT.json').write_bytes(a.staging_receipt.read_bytes())
    class TimingBackend(W.Backend87):
        def sweep(self,*args):
            values=super().sweep(*args)
            for v in values:json.dumps(v,allow_nan=False)
            return values
    b=TimingBackend(a.assets);b.hardware_assignment=ass
    timer=threading.Timer(max(0,end-time.time()-60),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    status='FAILED'
    try:
        measure(a.inputs,items,plan,b,a.out,binding,end,staging);status='PROFILE_ONLY'
    except BaseException as error:
        W.write(a.out/'FAILURE.json',dict(type=type(error).__name__,production_allowed=False));raise
    finally:
        timer.cancel();W.seal(a.out,'OUTPUT_SEAL.json',**binding,status=status,**W.first_output(a.out))



def validate_production(assignment,limits,plan,inp,source_sha):
    m=limits['timing95']
    if m.get('method') in ('REPRESENTATIVE_PHASE_WIDTH_V1','REPRESENTATIVE_PHASE_WIDTH_V2_SECTION217','REPRESENTATIVE_PHASE_WIDTH_V3_AMENDMENT1'):
        from representative95 import validate_production as validate_representative
        return validate_representative(assignment,limits,plan,inp,source_sha)
    from contract import digest
    W.require(m['source_seal_sha256']==source_sha and m['plan_sha256']==W.sha(inp/'PLAN.json') and
        m['items_sha256']==W.sha(inp/'items.json') and m['reduction_step']==plan['reduction_step'] and
        plan['row_indices']==[m['row']] and limits['cap_seconds']==m['cap_seconds'],'exact measured production source/row/cap')
    for k in ['gpu_type','image_digest','stack_sha256','assets_sha256','scope_seal_sha256','inventory_sha256','index_sha256']:
        W.require(assignment[k]==m[k],'production must match measured '+k)
    W.require(assignment['measured_profile_sha256']==m['profile_sha256'] and digest(m['output_seal_sha256']) and
        assignment['measured_decision_sha256']==m['measured_decision_sha256'] and
        digest(assignment['e95_integrator_admission_sha256']),'measured binding and independent I3 admission required')

if __name__=='__main__':main()
