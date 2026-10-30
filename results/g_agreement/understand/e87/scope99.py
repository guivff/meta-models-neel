"""E99 per-item position adapter for Backend87; public tokens only, no judging."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
from contract import read, write, sha, seal, verify, require, digest, deadline


SEED=20261030
FAMILIES=('hallucination','user_modeling','directed_modulation','agentic_misalignment','jailbreak_recognition','buggy_code')
PLACEBO=FAMILIES[:3]
BATCH=32


PARITY_AUTHORITY='a5bbbe493956b3f89a35b1beb56674d1d8cd7262'


def encoded_output(value):
    # Non-finite numerical output is still fatal, including during parity/warmup.
    return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode('utf-8')


def first_difference(a,b):
    return next((i for i in range(max(len(a),len(b))) if a[i:i+1]!=b[i:i+1]),None)


def report_parity(batched,serial,path,ids,batch_size):
    require(len(batched)==len(serial)==len(ids) and ids,'parity coverage')
    records=[]
    for identity,a,b in zip(ids,batched,serial):
        x,y=encoded_output(a),encoded_output(b)
        records.append(dict(id=identity,equal=x==y,batched_sha256=hashlib.sha256(x).hexdigest(),
            serial_sha256=hashlib.sha256(y).hexdigest(),first_divergence_position=first_difference(x,y),
            readout_first_divergence_position=first_difference(a['raw'].encode('utf-8'),b['raw'].encode('utf-8'))))
    receipt=dict(status='PASS' if all(r['equal'] for r in records) else 'MISMATCH_REPORTED',
        authority=PARITY_AUTHORITY,mismatch_is_gate=False,n=len(records),match_count=sum(r['equal'] for r in records),
        first_divergence_positions=[r['first_divergence_position'] for r in records],
        position_unit='zero-based UTF-8 byte in canonical serialized output',readout_position_unit='zero-based UTF-8 byte in raw readout',
        production_batch_size=batch_size,exact_serialized_output=True,records=records)
    write(path,receipt)
    return receipt


def checked_sweep(b,reader,vectors,layer):
    require(np.isfinite(vectors).all(),'non-finite reader input')
    values=b.sweep(reader,vectors,layer)
    require(len(values)==len(vectors),'native batch coverage')
    for value in values:encoded_output(value)
    return values


def layers(item, reduction=0):
    if item['family']=='buggy_code':return [44,item['family_layer']]
    if item['family']=='agentic_misalignment':return [36,44,56]
    return [20,36,44,56] if reduction==0 else [36,44,56]


def positions(item, layer, reduction=0):
    grid=item['positions']
    if item['family']=='agentic_misalignment' and reduction>=2:grid=grid[-64:]
    # Clarification1: onset is an extra arm only at Oracle44/NLA42.
    return sorted(set(grid+([item['single_position']] if layer in (42,44) else [])))


def validate(items, plan):
    require(set(plan)=={'experiment','seed','reduction_step','owner_seal_sha256','items_sha256','shards','shard','item_ids'},'public plan allowlist')
    require(plan['experiment']=='E99' and plan['seed']==SEED and plan['reduction_step'] in range(4),'E99 registration')
    require(digest(plan['owner_seal_sha256']) and digest(plan['items_sha256']),'owner binding')
    require(type(plan['shards']) is int and 4<=plan['shards']<=8 and 0<=plan['shard']<plan['shards'],'4–8 shards')
    require(items and len({x['id'] for x in items})==len(items),'unique nonempty bank')
    for x in items:
        require(set(x)=={'id','family','ids','positions','single_position','family_layer','placebo_ids'},'public item allowlist')
        require(isinstance(x['id'],str) and x['id'] and x['family'] in FAMILIES,'opaque ID/family')
        require(x['ids'] and all(type(t) is int and t>=0 for t in x['ids']),'token IDs')
        require(x['positions'] and x['positions']==sorted(set(x['positions'])) and
                all(type(p) is int and 0<=p<len(x['ids']) for p in x['positions']),'frozen position list')
        require(type(x['single_position']) is int and 0<=x['single_position']<len(x['ids']),'single position')
        require(x['family_layer'] in (56,60) if x['family']=='buggy_code' else x['family_layer'] is None,'family layer')
        if x['family']=='agentic_misalignment':require(x['positions']==list(range(max(0,len(x['ids'])-128),len(x['ids']))),'agentic last128')
        if x['family']=='buggy_code':require(x['positions']==[len(x['ids'])-1] and x['single_position']==len(x['ids'])-1,'EOF')
        if x['family']=='hallucination':require(x['single_position']==x['positions'][-1],'last hallucination site')
        if x['family']=='user_modeling':require(x['single_position'] in x['positions'],'onset in user modeling grid')
        require(isinstance(x['placebo_ids'],list) and all(isinstance(i,str) and len(i)==24 and all(c in '0123456789abcdef' for c in i) for i in x['placebo_ids']),'pseudo indices')
        if x['family'] not in PLACEBO:require(not x['placebo_ids'],'registered placebo families only')
    require(set(x['family'] for x in items)==set(FAMILIES),'complete six-family owner bank')
    for family in PLACEBO:
        ids=[i for x in items if x['family']==family for i in x['placebo_ids']]
        require(len(ids)==len(set(ids))==30,'exactly30 paired pseudo-items per family')
    require(plan['item_ids']==[x['id'] for x in shard_items(items,plan)],'deterministic family/item shard')
    return items


def shard_items(items,plan):
    """Whole items, greedy balanced cell count; immutable ID tiebreak, no outcomes."""
    loads=[0]*plan['shards'];assigned={}
    eligible=[x for x in items if not(plan['reduction_step']>=3 and x['family']=='jailbreak_recognition')]
    cost=lambda x:sum(len(positions(x,l,plan['reduction_step'])) for l in layers(x,plan['reduction_step'])+[42])*(1+len(x['placebo_ids']))
    for x in sorted(eligible,key=lambda x:(-cost(x),x['family'],x['id'])):
        s=min(range(len(loads)),key=lambda i:(loads[i],i));assigned[x['id']]=s;loads[s]+=cost(x)
    return [x for x in sorted(eligible,key=lambda x:(x['family'],x['id'])) if assigned[x['id']]==plan['shard']]


def key(item):return hashlib.sha256(item['id'].encode()).hexdigest()


def capture(items,plan,b,c,out,binding):
    import worker87 as W
    root=out/'capture';root.mkdir()
    c.call('oracle_setup',b.load_oracle)
    c.call('capture_warmup_discarded',b.warm_capture)
    index=[]
    for item in shard_items(items,plan):
        ls=layers(item,plan['reduction_step'])+[42]
        got=c.call('capture',lambda:b.capture_all(item,ls),real=True)
        row=dict(id=item['id'],family=item['family'],files={})
        for l in ls:
            ps=positions(item,l,plan['reduction_step']);h=np.asarray(got[l])[ps].astype(np.float32)
            require(h.shape==(len(ps),W.DIM) and np.isfinite(h).all(),'capture positions/shape')
            name=f'{key(item)}_{l}.npy';np.save(root/name,h,allow_pickle=False)
            row['files'][str(l)]=dict(path=name,positions=ps,grid_positions=[p for p in ps if p in item['positions']])
        index.append(row)
    write(root/'INDEX.json',index)
    seal(root,'CAPTURE_SEAL.json',**binding,items_sha256=plan['items_sha256'],reduction_step=plan['reduction_step'],reader_outputs=0)
    return root


def cells(items,plan):
    grouped=defaultdict(list)
    for item in shard_items(items,plan):
        for l in layers(item,plan['reduction_step'])+[42]:
            reader='nla' if l==42 else 'oracle'
            for pseudo in [None]+item['placebo_ids']:
                for p in positions(item,l,plan['reduction_step']):
                    grouped[reader,l,item['family']].append(dict(unit_id=item['id'] if pseudo is None else pseudo,paired_capture_id=item['id'],family=item['family'],reader=reader,layer=l,position=p,
                        arm='real' if pseudo is None else 'placebo',pseudo_id=pseudo,
                        grid=p in (item['positions'][-64:] if item['family']=='agentic_misalignment' and plan['reduction_step']>=2 else item['positions']),
                        single_site=l in (42,44) and p==item['single_position']))
    return grouped


def random_vector(cell,median,dim):
    from worker87 import norm_match
    # Identical Gaussian across layers/readers, stable under all shard/reduction choices.
    payload=f"{SEED}:{cell['family']}:{cell['pseudo_id']}:{cell['position']}".encode()
    entropy=np.frombuffer(hashlib.sha256(payload).digest(),dtype='<u4').tolist()
    z=np.random.default_rng(np.random.SeedSequence([SEED]+entropy)).standard_normal((1,dim)).astype(np.float32)
    return norm_match(z,np.array([median],np.float64))[0]


def output_provenance(out):
    paths=[p for p in (out/'jobs').glob('*.json')]+[p for p in out.glob('PARITY_*.json')]
    if not paths:return dict(first_output_utc='unknown',first_output_evidence=None)
    p=min(paths,key=lambda p:p.stat().st_mtime_ns)
    return dict(first_output_utc=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),
        first_output_evidence=dict(member=str(p.relative_to(out)),sha256=sha(p),mtime_ns=p.stat().st_mtime_ns,source='file mtime'))


def acquire(items,plan,b,c,out,binding,root,profile=False):
    import worker87 as W
    cap=verify(root,'CAPTURE_SEAL.json',sha(root/'CAPTURE_SEAL.json'))
    require(cap['items_sha256']==plan['items_sha256'] and cap['reduction_step']==plan['reduction_step'] and
            cap['shard']==plan['shard'] and cap.get('source_seal_sha256')==binding.get('source_seal_sha256'),'capture binding')
    matrices={};indices={}
    for row in read(root/'INDEX.json'):
        for l,e in row['files'].items():
            matrices[row['id'],int(l)]=np.load(root/e['path'],allow_pickle=False)
            indices[row['id'],int(l)]={p:i for i,p in enumerate(e['positions'])}
    groups=cells(items,plan);jobs=out/'jobs';jobs.mkdir();b.sweep_batch_size=BATCH
    counts={};profile_rows=[];parity_counts=defaultdict(int);parity_matches=defaultdict(int);parity_receipts=[]
    c.call('oracle_setup',b.load_oracle)
    for reader in ('oracle','nla'):
        if reader=='nla':c.call('nla_setup',b.load_nla)
        for (r,l,family),group in sorted(groups.items()):
            if r!=reader:continue
            chunks=[group[i:i+BATCH] for i in range(0,len(group),BATCH)]
            c.remaining[f'{reader}_{l}_{family}']=len(chunks)
            dummy=np.random.default_rng(SEED+l).standard_normal((BATCH,W.DIM)).astype(np.float32)
            c.call(f'{reader}_{l}_{family}_warmup_discarded',lambda:checked_sweep(b,reader,dummy,l))
            selected=chunks[:3] if profile else chunks
            def vectors(chunk):
                hs=[]
                for cell in chunk:
                    h=matrices[cell['paired_capture_id'],l][indices[cell['paired_capture_id'],l][cell['position']]]
                    if cell['arm']=='placebo':
                        target=float(np.linalg.norm(h.astype(np.float64)))
                        h=random_vector(cell,target,W.DIM)
                    hs.append(h)
                return np.stack(hs)
            # Spread parity over distinct items where available, rather than eight adjacent positions.
            first=[];seen=set()
            for cell in group:
                if cell['unit_id'] not in seen:
                    first.append(cell);seen.add(cell['unit_id'])
                    if len(first)==8:break
            rest=[cell for cell in group if cell not in first]
            probe=(first+rest)[:BATCH];h=vectors(probe);n=min(8,len(probe))
            batched=c.call(f'{reader}_{l}_{family}_parity_batch',lambda:checked_sweep(b,reader,h,l))
            serial=[c.call(f'{reader}_{l}_{family}_serial_parity',lambda i=i:checked_sweep(b,reader,h[i:i+1],l))[0] for i in range(n)]
            parity=report_parity(batched[:n],serial,out/f'PARITY_{reader}_{l}_{family}.json',
                [f"{x['unit_id']}:{x['position']}" for x in probe[:n]],BATCH)
            parity_counts[reader]+=n;parity_matches[reader]+=parity['match_count']
            parity_receipts.append(dict(reader=reader,layer=l,family=family,**parity))
            for j,chunk in enumerate(selected):
                h=vectors(chunk);before=h.tobytes()
                values=c.call(f'{reader}_{l}_{family}',lambda:checked_sweep(b,reader,h,l),real=True)
                require(len(values)==len(chunk) and h.tobytes()==before,'unaltered native batch')
                write(jobs/f'{reader}_{l}_{family}_{j:06d}.json',[dict(cell,id=f"{cell['unit_id']}:{reader}:{l}:{cell['position']}",**v) for cell,v in zip(chunk,values)])
                c.remaining[f'{reader}_{l}_{family}']-=1
                # Every batch is subject to the absolute admitted deadline. Profile forecast is below.
            counts[f'{reader}:{l}:{family}']=sum(len(x) for x in selected)
            profile_rows.append(dict(reader=reader,layer=l,family=family,total_batches=len(chunks),measured_batches=len(selected),
                mean_seconds=float(np.mean(c.observed[f'{reader}_{l}_{family}'])),batch_sizes=[len(x) for x in selected]))
            c.remaining[f'{reader}_{l}_{family}']=0
    require(all(parity_counts[r]>=8 for r in ('oracle','nla')),'at least8 parity cells per reader across layers')
    write(out/'PARITY_SUMMARY.json',dict(authority=PARITY_AUTHORITY,mismatch_is_gate=False,
        n=sum(parity_counts.values()),match_count=sum(parity_matches.values()),receipts=parity_receipts))
    if profile:
        gen=sum(x['total_batches']*x['mean_seconds'] for x in profile_rows)
        overhead=sum(x['seconds'] for x in c.events if not x['real'] or x['phase']=='capture')
        write(out/'MEASURED_PROFILE.json',dict(binding,status='TIMING_ONLY_NOT_SCIENCE',items_sha256=plan['items_sha256'],
            reduction_step=plan['reduction_step'],batch_size=BATCH,parity_items=8,parity_counts=dict(parity_counts),parity_matches=dict(parity_matches),parity_mismatch_is_gate=False,
            parity_authority=PARITY_AUTHORITY,parity_receipt_sha256=sha(out/'PARITY_SUMMARY.json'),rows=profile_rows,
            forecast_seconds=1.25*(gen+overhead+60),margin=1.25,
            norm_rule='paired real norm at each reader/layer/position',profile_outputs_discarded=True,**output_provenance(out)))
    else:
        require(counts=={f'{r}:{l}:{f}':len(v) for (r,l,f),v in groups.items()},'complete grid')
        write(out/'COUNTS.json',counts)


def main(argv=None):
    from worker87 import Backend87,HERE,ROOT,Clock
    p=argparse.ArgumentParser()
    for k in ('inputs','assets','assignment','out'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
    p.add_argument('--stage99',choices=('capture','profile','read'),required=True)
    p.add_argument('--capture-root',type=Path);p.add_argument('--measured-profile',type=Path)
    a=p.parse_args(argv)
    verify(HERE,'SOURCE_SEAL.json',a.source_sha)
    for name,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==h,'dependency '+name)
    s=verify(a.inputs,'INPUT_SEAL.json',a.input_sha)
    require(set(s['files'])=={'items.json','PLAN.json','STAGE_REQUEST.json'} and
            {str(f.relative_to(a.inputs)) for f in a.inputs.rglob('*') if f.is_file()}==set(s['files'])|{'INPUT_SEAL.json'},'public inputs only')
    plan=read(a.inputs/'PLAN.json');items=validate(read(a.inputs/'items.json'),plan)
    require(sha(a.inputs/'items.json')==plan['items_sha256'],'full frozen bank bytes')
    ass=read(a.assignment);limits=read(a.inputs/'STAGE_REQUEST.json')
    require(ass['shard']==plan['shard'] and ass['stage99']==a.stage99 and limits['status']=='READY','assignment stage')
    if a.stage99=='read':
        require(a.capture_root and sha(a.capture_root/'CAPTURE_SEAL.json')==ass['capture_seal_sha256'],'sealed capture required for admitted reader run')
        require(a.measured_profile and sha(a.measured_profile)==ass['measured_profile_sha256']==limits['measured_profile_sha256'] and
                ass['admission_sha256']==limits['admission_sha256'],'measured profile and aggregate admission identity')
        measured=read(a.measured_profile)
        require(measured['status']=='TIMING_ONLY_NOT_SCIENCE' and measured['margin']==1.25 and measured['parity_items']==8 and
                measured['items_sha256']==plan['items_sha256'] and measured['reduction_step']==plan['reduction_step'] and
                measured['source_seal_sha256']==a.source_sha and measured['shard']==plan['shard'] and
                ass['cap_seconds']>=math.ceil(measured['forecast_seconds']),'same-source measured cap with1.25 margin required')
    end=deadline(ass,limits,time.time());a.out.mkdir(parents=True,exist_ok=False)
    write(a.out/'ASSIGNMENT.json',ass)
    b=Backend87(a.assets);c=Clock(a.out,end,limits['seed_seconds_per_batch'],b)
    binding=dict(experiment='E99',shard=plan['shard'],source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,pod_id=ass['pod_id'])
    # Same hard wall-clock guard as E87, including a stuck model call.
    import os,signal,threading
    timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    status='FAILED'
    try:
        root=a.capture_root or capture(items,plan,b,c,a.out,binding)
        if a.stage99!='capture':acquire(items,plan,b,c,a.out,binding,root,a.stage99=='profile')
        status={'capture':'CAPTURE_ONLY','profile':'PROFILE_ONLY','read':'COMPLETE'}[a.stage99]
    finally:
        timer.cancel();seal(a.out,'OUTPUT_SEAL.json',**binding,status=status,**output_provenance(a.out))

if __name__=='__main__':main()
