"""§198 deviation1: serial greedy, item-disjoint shards, timing first; no parity."""
import argparse
from datetime import datetime,timezone
import math
import os
from pathlib import Path
import signal
import threading
import time
import worker81 as W
from runtime import Runtime
AUTHORITY='5ad0c3ced8430faa24b76676112e8ba9c9766639'


def roster(items,n):
    W.require(type(n)is int and 1<=n<=8,'one to eight shards')
    return [[x['id'] for i,x in enumerate(items) if i%n==s] for s in range(n)]


def probe_items(items,ids):
    selected=set(ids);out=[]
    for limit in (128,32):
        group=sorted((x for x in items if x['id'] in selected and x['max_new_tokens']==limit),key=lambda x:(len(x['input_ids']),x['id']))
        W.require(len(group)>=3,'three timing items per phase/shard')
        out.extend(group[i] for i in (0,len(group)//2,len(group)-1))
    return out


def provenance(out):
    paths=list((out/'jobs').glob('*.json'))
    if not paths:return dict(first_output_utc='unknown',first_output_evidence=None)
    p=min(paths,key=lambda p:p.stat().st_mtime_ns)
    return dict(first_output_utc=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),
        first_output_evidence=dict(member=str(p.relative_to(out)),sha256=W.sha(p),mtime_ns=p.stat().st_mtime_ns,source='file mtime'))


def staging_receipt(assignment,worker_ready_epoch,assignment_sha256):
    created=assignment['pod_created_epoch']
    W.require(all(type(x) in (int,float) and math.isfinite(x) for x in (created,worker_ready_epoch)) and
        created<=worker_ready_epoch,'finite original creation-to-worker interval')
    W.require(assignment['custody_start_epoch']==created,'E81 custody starts at original provider creation')
    return dict(pod_id=assignment['pod_id'],assignment_sha256=assignment_sha256,
        provider_created_epoch=created,worker_ready_epoch=worker_ready_epoch,
        staging_seconds=worker_ready_epoch-created,
        interval='original provider creation through worker verification; before model setup')


def acquire(items,plan,b,c,out,binding):
    shards=roster(items,plan['shards']);byid={x['id']:x for x in items}
    W.require(plan['authority']==AUTHORITY and plan['shard_ids']==shards,'frozen complete shard roster')
    profile=plan['mode']=='profile';W.require(profile or plan['mode']=='production','mode')
    staging=staging_receipt(W.read(out/'ASSIGNMENT.json'),time.time(),W.sha(out/'ASSIGNMENT.json'))
    W.write(out/'STAGING_RECEIPT.json',staging)
    c.call('base_setup',b.load_base)
    c.call('tokenizer_verification',lambda:b.check_tokens([dict(text=x['prompt'],ids=x['input_ids']) for x in items]))
    for limit in (128,32):
        c.call(f'warmup{limit}_discarded',lambda:b.text([b.synthetic()[0]],max_new_tokens=limit))
    jobs=out/'jobs';jobs.mkdir();seen=[];stats=[]
    selected_shards=range(plan['shards']) if profile else [plan['shard']]
    for shard in selected_shards:
        xs=probe_items(items,shards[shard]) if profile else [byid[i] for i in shards[shard]]
        for j,x in enumerate(xs):
            phase=f'shard{shard}_text{x["max_new_tokens"]}'
            values=c.call(phase,lambda:b.text([x['input_ids']],max_new_tokens=x['max_new_tokens']),real=True)
            W.require(len(values)==1,'serial generation only')
            W.write(jobs/f'{shard}_{j:06d}.json',[dict(id=x['id'],text=values[0]['raw'],token_ids=values[0]['token_ids'],max_new_tokens=x['max_new_tokens'])])
            seen.append(x['id'])
        if profile:
            means={str(limit):sum(c.observed[f'shard{shard}_text{limit}'])/3 for limit in (128,32)}
            counts={str(limit):sum(byid[i]['max_new_tokens']==limit for i in shards[shard]) for limit in (128,32)}
            setup=sum(x['seconds'] for x in c.events if not x['real'])
            forecast=1.25*(sum(counts[k]*means[k] for k in means)+staging['staging_seconds']+setup+60)
            stats.append(dict(shard=shard,items=len(shards[shard]),phase_counts=counts,seconds_per_item=means,
                staging_seconds=staging['staging_seconds'],setup_warmup_seconds=setup,retrieval_reserve_seconds=60,forecast_seconds=forecast,cap_seconds=math.ceil(forecast)))
    W.require(len(seen)==len(set(seen)),'no duplicate item acquisition')
    if profile:
        W.write(out/'MEASURED_PROFILE.json',dict(binding,status='SERIAL_TIMING_ONLY_NOT_SCIENCE',authority=AUTHORITY,
            staging=staging,staging_receipt_sha256=W.sha(out/'STAGING_RECEIPT.json'),
            batch_size=1,parity_gate=False,items_per_phase_per_shard=3,margin=1.25,shards=stats,
            profile_outputs_discarded=True,regenerate_all_11064=True,**provenance(out)))
    else:
        W.require(seen==shards[plan['shard']],'entire frozen shard')
        W.write(out/'COUNTS.json',dict(items=len(seen),shard=plan['shard'],batch_size=1,parity_gate=False))


def main():
    p=argparse.ArgumentParser()
    for name in ('inputs','assets','assignment','out'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('source-sha','input-sha'):p.add_argument('--'+name,required=True)
    p.add_argument('--profile-report',type=Path);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    W.verify(W.HERE,'SOURCE_SEAL.json',a.source_sha)
    for name,h in W.read(W.HERE/'DEPENDENCIES.json').items():W.require(W.sha(W.ROOT/name)==h,'dependency '+name)
    s=W.verify(a.inputs,'INPUT_SEAL.json',a.input_sha)
    expected={'PUBLIC_INPUTS.json','STAGE_REQUEST.json','SERIAL_PLAN.json'}
    W.require(set(s['files'])==expected and {x.name for x in a.inputs.iterdir()}==expected|{'INPUT_SEAL.json'},'public-only input archive')
    items=W.validate(W.read(a.inputs/'PUBLIC_INPUTS.json'));plan=W.read(a.inputs/'SERIAL_PLAN.json');limits=W.read(a.inputs/'STAGE_REQUEST.json');ass=W.read(a.assignment)
    W.require(plan['public_inputs_sha256']==W.sha(a.inputs/'PUBLIC_INPUTS.json') and limits['batch_size']==1,'serial public-bank binding')
    W.require(ass['mode']==plan['mode'] and ass['shard']==plan['shard'] and limits['status']=='READY','mode/shard assignment')
    if plan['mode']=='production':
        W.require(a.profile_report and W.sha(a.profile_report)==plan['measured_profile_sha256'],'measured report binding')
        m=W.read(a.profile_report)
        W.require(m['status']=='SERIAL_TIMING_ONLY_NOT_SCIENCE' and m['source_seal_sha256']==a.source_sha and
            m['public_inputs_sha256']==plan['public_inputs_sha256'] and not m['synthetic'] and m['margin']==1.25 and
            m['batch_size']==1 and len(m['shards'])==plan['shards'],'same-source serial timing')
        forecast=m['shards'][plan['shard']]
        W.require(forecast['shard']==plan['shard'] and ass['cap_seconds']==forecast['cap_seconds'],'measured times1.25 cap')
    staging_receipt(ass,time.time(),W.sha(a.assignment))
    end=W.deadline(ass,limits,time.time());a.out.mkdir(parents=True,exist_ok=False);W.write(a.out/'ASSIGNMENT.json',ass)
    if a.dry_run:
        from test_worker81 import Tiny81
        b=Tiny81()
    else:b=Runtime(a.assets)
    c=W.Clock(a.out,end,{},b)
    binding=dict(experiment='E81',includes='E90',source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,
        public_inputs_sha256=plan['public_inputs_sha256'],pod_id=ass['pod_id'],synthetic=a.dry_run,**getattr(b,'hardware_metadata',{}))
    timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='FAILED'
    try:
        acquire(items,plan,b,c,a.out,binding);status='PROFILE_ONLY' if plan['mode']=='profile' else 'COMPLETE'
    finally:
        timer.cancel();W.seal(a.out,'OUTPUT_SEAL.json',**binding,status=status,**provenance(a.out))

if __name__=='__main__':main()
