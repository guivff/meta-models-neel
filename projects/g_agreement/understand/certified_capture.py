"""§144 conditional capture routing and fail-closed E24-E release evidence."""
import json,sys
from collections import defaultdict
from pathlib import Path
from projects.g_agreement.blindspot import protocol as P,run as W
from .e24_clone_capture import capture as clone_capture
PREFIX={'G':'/weights/venv','E':'/weights/venv-kernels','C':'/weights/venv','D':'/weights/venv-kernels'}

def release(plan,assignment,certificate,context,check_environment=True):
    P.verify(certificate,'ANALYSIS_SEAL.json')
    P.verify(certificate,'DIAGNOSTIC_SEAL.json')
    if P.sha(certificate/'ANALYSIS_SEAL.json')!=assignment.get('diagnostic_analysis_seal_sha256'):raise ValueError('diagnostic certificate binding')
    decision=json.loads((certificate/'DECISION.json').read_text());strata=json.loads((certificate/'STRATA.json').read_text())
    mode=decision.get('certified_arm');allowed={'G':['G'],'E':['E'],'CD':['C','D']}[plan['capture_mode']]
    if decision.get('status')!='CAPTURE_MODE_CERTIFIED' or mode not in allowed:raise ValueError('uncertified requested capture mode')
    ruling146=plan.get('operations_authority')=='d0f72b00' and plan['capture_mode']=='G' and mode=='G'
    if not ruling146 and (strata['C']['minimum_W1']<.999 or decision['below_0999']['C']!=0):
        raise ValueError('section144 C/W1 failure: all capture-dependent work held')
    if check_environment:
        if sys.prefix!=PREFIX[mode]:raise ValueError('certified environment mismatch')
        import importlib.metadata as md
        actual={d.metadata['Name'].lower():d.version for d in md.distributions() if d.metadata.get('Name')}
        environment='w1' if mode in ('G','C') else 'kernels'
        expected=json.loads((certificate/f'ENV_{environment}.json').read_text())['packages']
        for name in ('torch','transformers','peft','causal-conv1d','fla-core','flash-linear-attention'):
            if actual.get(name)!=expected.get(name):raise ValueError('certified package mismatch: '+name)
    P.verify(context,'INPUT_SEAL.json')
    if P.sha(context/'INPUT_SEAL.json')!=plan['capture_context_seal_sha256']:raise ValueError('capture context binding')
    return mode

def batches(items,mode,context):
    selected={x['id']:x for x in items}
    if len(selected)!=len(items):raise ValueError('duplicate capture items')
    if mode=='G':
        lookup={x['id']:x for x in P.rows(context/'items.input.jsonl')}
        groups=[b for b in json.loads((context/'layout.json').read_text()) if selected.keys() & set(b['ids'])]
        for x in items:
            if x['id'] not in lookup or x['ids']!=lookup[x['id']]['ids']:raise ValueError('W1 capture context token mismatch')
        seen=[uid for b in groups for uid in b['ids'] if uid in selected]
        if len(seen)!=len(items) or set(seen)!=set(selected):raise ValueError('original layout missing/repeated items')
        return [(b,[lookup[u] for u in b['ids']]) for b in groups]
    if mode in ('C','D'):return [({'unit':'batch1','start':i},[x]) for i,x in enumerate(items)]
    if mode!='E':raise ValueError('unknown mode')
    bucket=defaultdict(list)
    for x in items:bucket[len(x['ids'])].append(x)
    return [({'unit':f'exact_length_{n}','start':start},xs[start:start+32]) for n,xs in sorted(bucket.items()) for start in range(0,len(xs),32)]

def capture(ol,items,layers,mode,context):
    import torch,mats.capture
    selected={x['id'] for x in items};bylayer={l:{} for l in layers};metadata=[]
    groups=batches(items,mode,context)
    # G always forwards through the full certified grid; extra E32 layers retain clones.
    requests=[sorted(set(layers)|set(range(20,61,4)))] if mode=='G' else [([42,44] if l==44 else [l]) for l in layers]
    previous=mats.capture.capture;mats.capture.capture=clone_capture
    try:
        for info,batch in groups:
            width=max(len(x['ids']) for x in batch)
            for pos,x in enumerate(batch):
                if x['id'] in selected:metadata.append({'id':x['id'],'row':x['feature'],'token_count':len(x['ids']),'read_position':len(x['ids'])-1,'padding_length':width-len(x['ids']),'batch_position':pos,'batch_size':len(batch),'environment':PREFIX[mode],'capture_mode':mode,**info})
            for requested in requests:
                acts,scores=W.capture_and_score(batch,None,{},ol,None,batch=1 if mode in ('C','D') else 32,capture_layers=requested)
                if scores:raise ValueError('capture must not score')
                for l in layers:
                    if l not in acts:continue
                    for pos,x in enumerate(batch):
                        if x['id'] in selected:bylayer[l][x['id']]=acts[l][pos]
    finally:mats.capture.capture=previous
    if any(set(v)!=selected for v in bylayer.values()):raise ValueError('capture coverage')
    return {l:torch.stack([v[x['id']] for x in items]) for l,v in bylayer.items()},metadata

def parity_gate(actual,reference,dest,items):
    import numpy as np
    from .e24_worker import parity
    try:r=parity(actual,reference)
    except Exception:
        x=np.asarray(actual,dtype=float);y=np.asarray(reference,dtype=float)
        if x.shape==y.shape and x.ndim==2:
            norms=np.linalg.norm(x,axis=1)*np.linalg.norm(y,axis=1)
            cs=np.divide((x*y).sum(1),norms,out=np.full(len(x),np.nan),where=norms>0)
            P.jsonl(dest/'PARITY_FAILURE_ITEMS.jsonl',[{'id':it['id'],'cosine':float(v) if np.isfinite(v) else None} for it,v in zip(items,cs)])
        raise
    P.dump(dest/'PARITY.json',r);return r
