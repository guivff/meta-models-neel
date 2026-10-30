"""§87 integrator-only dual-position capture and sealed, label-free scoring."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import signal
import time
from . import protocol as P
from . import run as W1
from .w11_items import source_hashes, SECTION

READERS=(('olens',44),('nla',42),('jlens',44))
BATCH_CAPTURE=8
BATCH_READER=16


def seal_named(out, names, filename, status):
    P.dump(Path(out)/filename,{'status':status,'files':{n:P.sha(Path(out)/n) for n in names}})


def allocation(forecast):
    if not math.isfinite(forecast) or forecast<=0:
        raise ValueError('invalid forecast')
    budget=min(1.5*forecast+360,3600)
    if forecast>budget:
        raise ValueError('NO_FIT: complete forecast exceeds capped allocation')
    return budget


def admit(assignment, bank, now=None, pod_id=None):
    now=time.time() if now is None else now
    a=json.loads(Path(assignment).read_text())
    pod_id=pod_id or os.environ.get('RUNPOD_POD_ID')
    if not pod_id or a.get('pod_id')!=pod_id or a.get('issuer')!='integrator' or a.get('experiment')!='W11':
        raise ValueError('exact integrator W11 assignment required')
    if any(a.get(k) is not True for k in ('brief_registered','brief_pushed','manifest_committed','external_hardstop_verified')):
        raise ValueError('published registration, committed manifest and independent guard required')
    for field in ('source_commit','brief_commit','manifest_commit'):
        s=a.get(field,'')
        if len(s)!=40 or any(c not in '0123456789abcdef' for c in s):raise ValueError('exact commit required: '+field)
    P.verify(bank,'INPUT_SEAL.json')
    manifest=json.loads((Path(bank)/'manifest.json').read_text())
    if manifest['experiment']!='W11' or a['brief_commit']!=manifest['registration']['commit']:
        raise ValueError('wrong experiment or registered commit')
    if a.get('source_files')!=source_hashes() or manifest['source_files']!=source_hashes():
        raise ValueError('source differs from frozen worker')
    if a.get('manifest_sha256')!=P.sha(Path(bank)/'manifest.json'):
        raise ValueError('manifest mismatch')
    if a.get('section87_sha256')!=P.sha(P.ROOT/SECTION) or manifest['section87_sha256']!=P.sha(P.ROOT/SECTION):
        raise ValueError('registration mismatch')
    budget=P._science_budget(a)
    created,deadline=float(a['provider_created_epoch']),float(a['deadline_epoch'])
    if (a.get('previous_gpu_seconds')!=0 or not 0<budget<=3600 or
            float(a.get('staging_allowance_seconds',-1))!=1500 or
            not all(math.isfinite(v) for v in (now,created,deadline)) or
            not created<=now<created+1500 or not 0<deadline-created<=float(a['allocated_gpu_seconds'])):
        raise ValueError('invalid setup or science allocation; no automatic retries')
    a['_science_clock_path']=str(Path(assignment).resolve().with_suffix('.science-clock.json'))
    a['_assignment_sha256']=P.sha(assignment)
    if Path(a['_science_clock_path']).exists():raise ValueError('existing clock: no duplicate/restart')
    P.science_deadline(a,now=now)
    return a


def inputs(bank):
    bank=Path(bank);P.verify(bank,'INPUT_SEAL.json');W1._labels_absent(bank)
    items=P.rows(bank/'items.input.jsonl')
    specs=json.loads((bank/'templates.json').read_text())
    if len(items)!=1200 or len({x['id'] for x in items})!=1200 or len(specs)!=10:
        raise ValueError('wrong frozen scope')
    index={x['id']:i for i,x in enumerate(items)}
    pairs=defaultdict(list)
    for x in items:
        if set(x)!={'id','feature','ids','donor_id','pair_id','target_start','positions'}:
            raise ValueError('worker input forbids labels and unregistered metadata')
        start=x['target_start'];ids=x['ids']
        if (type(start) is not int or not 0<start<len(ids) or x['positions']!=[start-1,len(ids)-1]
                or any(type(t) is not int or t<0 for t in ids) or x['donor_id'] not in index):
            raise ValueError('invalid positions, tokens or donor')
        d=items[index[x['donor_id']]]
        if d['feature']!=x['feature'] or len(d['ids'])//16!=len(ids)//16:
            raise ValueError('donor crosses row or length bin')
        pairs[x['pair_id']].append(x)
        for name,_ in READERS:W1._pairs(specs[x['feature']],name)
    if set(specs)!={x['feature'] for x in items} or len(pairs)!=600:
        raise ValueError('feature/pair coverage mismatch')
    for pair in pairs.values():
        if len(pair)!=2:raise ValueError('incomplete input pair')
        a,b=pair;start=a['target_start']
        if (b['target_start']!=start or a['ids'][:start]!=b['ids'][:start] or len(a['ids'])!=len(b['ids'])
                or a['feature']!=b['feature'] or a['ids'][start:]==b['ids'][start:]):
            raise ValueError('input pair is not minimal')
    return items,[index[x['donor_id']] for x in items],specs


def capture_dual(model,tok,items,checkpoint,batch=BATCH_CAPTURE):
    """Capture actual pre-target and terminal vectors from each FULL sequence.

    Never copy a vector between pair members: the leak check must detect actual
    noncausality, position mistakes, stochastic effects or row-alignment errors.
    """
    import torch
    from mats.capture import capture
    values={42:[],44:[]}
    for start in range(0,len(items),batch):
        checkpoint();chunk=items[start:start+batch]
        h=capture(model,[x['ids'] for x in chunk],[42,44],[x['positions'] for x in chunk],
                  batch_size=batch,pad_id=tok.pad_token_id or 0)
        for layer in values:
            if h[layer].ndim!=3 or h[layer].shape[:2]!=(len(chunk),2) or not torch.isfinite(h[layer]).all():
                raise ValueError('invalid dual-position capture')
            values[layer].append(h[layer])
    return {layer:torch.cat(chunks) for layer,chunks in values.items()}


def reader_values(name,obj,h,spec):
    if name=='olens':return obj.paired_logodds_templates(h,44,W1._pairs(spec,name))
    if name=='nla':
        from mats.readers.nla import paired_logodds_templates
        return paired_logodds_templates(obj,h,W1._pairs(spec,name),batch=32)
    return W1.native_baseline_contrasts(obj,h,44,W1._pairs(spec,name))


def timed(fn):
    import torch
    torch.cuda.synchronize();start=time.monotonic();value=fn();torch.cuda.synchronize()
    return value,time.monotonic()-start


def forecast_work(items,specs,ol,jl,nla,check):
    """Three timed units per code path/row; extrapolate medians, never cold calls."""
    import statistics
    longest=sorted(items,key=lambda x:(len(x['ids']),x['id']),reverse=True)[:BATCH_CAPTURE]
    capture_times=[]
    with ol.base():
        for _ in range(3):
            _,elapsed=timed(lambda:capture_dual(ol.model,ol.tok,longest,check))
            capture_times.append(elapsed)
    forecast=statistics.median(capture_times)*math.ceil(len(items)/BATCH_CAPTURE)
    rows=[]
    for feature in specs:
        subset=[x for x in items if x['feature']==feature]
        sample=sorted(subset,key=lambda x:(len(x['ids']),x['id']),reverse=True)[:BATCH_READER]
        with ol.base():h=capture_dual(ol.model,ol.tok,sample,check)
        for name,obj,layer in (('olens',ol,44),('nla',nla,42),('jlens',jl,44)):
            times=[]
            for _ in range(3):
                check();_,elapsed=timed(lambda:reader_values(name,obj,h[layer][:,1],specs[feature]))
                times.append(elapsed)
            projected=statistics.median(times)*math.ceil(len(subset)/BATCH_READER)
            forecast+=projected
            rows.append({'feature':feature,'reader':name,'timed_unit_seconds':times,
                         'median_unit_seconds':statistics.median(times),'projected_seconds':projected})
    return forecast,{'capture_timed_seconds':capture_times,'capture_median_seconds':statistics.median(capture_times),
        'capture_batch':BATCH_CAPTURE,'reader_batch':BATCH_READER,'reader_rows':rows,
        'smoke_outputs_retained':False,'donor_cost':'exact reindexing of deterministic activation-only reader scores'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bank','assignment','assets','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assignment=admit(a.assignment,a.bank)
    items,donors,specs=inputs(a.bank);a.out.mkdir(parents=True,exist_ok=False)
    with P.logged('w11_capture_score',gpu=True),P.compute_window(assignment):
        assets=W1._assets(a.assets);ol=W1._load_oracle(assets)
        from mats.readers.jlens import load_jlens
        from mats.readers.nla import load_nla
        jl=load_jlens(ol.model,ol.tok,layers=[44],path=assets['jlens'])
        nla=load_nla(root=assets['nla'],load_ar=False,enable_thinking=False)
        ol.model.eval();nla.eval() if hasattr(nla,'eval') else None
        P.science_deadline(assignment)
        # Exactly one synthetic, unscored warm-up per capture/reader path in setup.
        warm_ids=list(ol.tok('A neutral record is available.\nred',add_special_tokens=False)['input_ids'])
        warm=[{'ids':warm_ids,'positions':[len(warm_ids)-2,len(warm_ids)-1]} for _ in range(BATCH_CAPTURE)]
        with ol.base():wh=capture_dual(ol.model,ol.tok,warm,lambda:P.science_deadline(assignment))
        synthetic={'olens':[('- A record.','- A note.'),('- A page.','- A sheet.')],
                   'nla':[('A record.','A note.'),('A page.','A sheet.')],
                   'jlens':[('record','note'),('page','sheet')]}
        for name,obj,layer in (('olens',ol,44),('nla',nla,42),('jlens',jl,44)):
            P.science_deadline(assignment);reader_values(name,obj,wh[layer][:,1].repeat(2,1),synthetic)
        import torch
        torch.cuda.synchronize();P.science_checkpoint(assignment)
        clock=json.loads(Path(assignment['_science_clock_path']).read_text());first=clock['first_science_epoch']
        deadline=[clock['science_deadline_epoch']]
        def check():
            P.science_checkpoint(assignment)
            if time.time()>=deadline[0]:raise TimeoutError('W11 science deadline reached')
            signal.setitimer(signal.ITIMER_REAL,max(.01,deadline[0]-time.time()))
        remaining,diagnostics=forecast_work(items,specs,ol,jl,nla,check)
        forecast=time.time()-first+remaining
        try:
            budget=allocation(forecast)
            if budget>P._science_budget(assignment) or time.time()+remaining>deadline[0]:
                raise ValueError('NO_FIT: available assignment cannot fit unchanged bank')
        except ValueError as exc:
            P.dump(a.out/'FORECAST.json',{'status':'NO_FIT','forecast_s':forecast,'reason':str(exc),**diagnostics})
            raise
        deadline[0]=min(deadline[0],first+budget)
        P.dump(a.out/'FORECAST.json',{'status':'FIT','forecast_s':forecast,'science_allocation_s':budget,
            'first_science_epoch':first,'science_deadline_epoch':deadline[0],**diagnostics})
        with ol.base():h=capture_dual(ol.model,ol.tok,items,check)
        import numpy as np
        for layer in (42,44):
            np.save(a.out/f'acts{layer}.npy',h[layer][:,1].numpy(),allow_pickle=False)
            np.save(a.out/f'pretarget.acts{layer}.npy',h[layer][:,0].numpy(),allow_pickle=False)
        P.dump(a.out/'items.order.json',[x['id'] for x in items])
        P.dump(a.out/'provenance.json',{'experiment':'W11','input_seal_sha256':P.sha(a.bank/'INPUT_SEAL.json'),
            'manifest_sha256':P.sha(a.bank/'manifest.json'),'source_files':source_hashes(),
            'assignment_sha256':P.sha(a.assignment),'assets_sha256':P.sha(a.assets),'first_science_epoch':first,
            'capture_positions':['actual pretarget position from full sequence','last target-span token'],
            'readers':READERS,'no_pair_vector_copy':True})
        capture_files=['acts42.npy','acts44.npy','pretarget.acts42.npy','pretarget.acts44.npy','items.order.json','provenance.json']
        seal_named(a.out,capture_files,'CAPTURE_SEAL.json','W11_CAPTURE_SEALED')
        groups=defaultdict(list)
        for i,x in enumerate(items):groups[x['feature']].append(i)
        scores=[]
        for feature,indices in groups.items():
            local={i:j for j,i in enumerate(indices)}
            for name,obj,layer in (('olens',ol,44),('nla',nla,42),('jlens',jl,44)):
                chunks=[]
                for start in range(0,len(indices),BATCH_READER):
                    check();idx=indices[start:start+BATCH_READER]
                    chunks.append(reader_values(name,obj,h[layer][idx,1],specs[feature]))
                values=torch.cat(chunks,dim=1)
                for arm,v in (('true',values),('random_donor',values[:,[local[donors[i]] for i in indices]])):
                    rows=W1._score_rows(items,indices,v,name,layer,arm,
                        'max_token_cosine_contrast' if name=='jlens' else 'summed_sequence_logodds')
                    scores.extend(rows)
                    with (a.out/'scores.partial.jsonl').open('a') as stream:
                        for row in rows:stream.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')
                        stream.flush();os.fsync(stream.fileno())
        P.jsonl(a.out/'scores.jsonl',scores)
        seal_named(a.out,['scores.jsonl','items.order.json','provenance.json','FORECAST.json','CAPTURE_SEAL.json'],
                   'SCORE_SEAL.json','SCORES_SEALED_W11_BEFORE_LABEL_JOIN')
        check();P.dump(a.out/'SCIENCE_RECEIPT.json',{'status':'COMPLETE_NO_LABEL_JOIN',
            'first_science_epoch':first,'completed_epoch':time.time(),'science_elapsed_s':time.time()-first,
            'science_deadline_epoch':deadline[0],'science_allocation_s':budget,'forecast_s':forecast})


if __name__=='__main__':main()
