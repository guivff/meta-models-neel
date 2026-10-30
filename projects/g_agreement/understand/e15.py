"""§105 scoring-only E15, reusing E6/W1 loaders and native likelihood scorers."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import statistics
import time
import numpy as np
from .e6 import K
from .e15_pairs import PAIRS
from projects.g_agreement.blindspot import protocol as P,run as R

FROZEN=K.RESULTS/'e15'
CAP=1800


def source_hashes():
    names=list(P.code_hashes())+['projects/g_agreement/understand/'+n for n in
        ('__init__.py','core.py','e6.py','e15_pairs.py','e15.py')]
    names+=['results/g_agreement/understand/e15/'+n for n in ('CONTINUATION_PAIRS.json','REGISTERED_SECTION.md')]
    return {n:P.sha(P.ROOT/n) for n in names}


def prepare():
    items,acts,specs=K.load_w1()
    bank=P.ROOT/'cache/g_agreement/understand/e15-stage-v1'
    w1_inputs=P.ROOT/'cache/g_agreement/blindspot/w1-bank-v2'
    P.verify(w1_inputs,'INPUT_SEAL.json')
    input_lookup={x['id']:x for x in P.rows(w1_inputs/'items.input.jsonl')}
    selected={split:[i for i,x in enumerate(items) if x['feature'] in PAIRS and x['split']==split] for split in ('dev','test')}
    if any(len(idx)!=672 for idx in selected.values()):raise ValueError('need84items/row/split')
    test=[items[i] for i in selected['test']];dev=[items[i] for i in selected['dev']]
    ids={x['id'] for x in test};groups=defaultdict(list)
    for x in test:groups[x['feature'],x['cluster'],len(x['ids'])//16].append(x['id'])
    random={}
    for x in test:
        pool=sorted(groups[x['feature'],x['cluster'],len(x['ids'])//16])
        draw=int(hashlib.sha256(('E15-random-donor:20261024:'+x['id']).encode()).hexdigest(),16)
        random[x['id']]=pool[draw%len(pool)]
        if input_lookup[x['id']]['donor_id'] not in ids:raise ValueError('frozen W1 mismatch outside test bank')
    bank.mkdir(parents=True,exist_ok=False)
    P.jsonl(bank/'items.input.jsonl',[{'id':x['id'],'feature':x['feature'],'random_donor_id':random[x['id']],
        'w1_mismatched_donor_id':input_lookup[x['id']]['donor_id']} for x in test])
    P.jsonl(bank/'reference.input.jsonl',[{'id':x['id'],'feature':x['feature'],'ids':x['ids']} for x in dev])
    for site in (42,44):np.save(bank/f'acts{site}.npy',np.asarray(acts[site][selected['test']]),allow_pickle=False)
    labels=P.ROOT/'cache/g_agreement/understand/e15.labels.DO_NOT_STAGE.jsonl'
    P.jsonl(labels,[{k:x[k] for k in ('id','feature','value','split','cluster')} for x in test+dev])
    shutil.copyfile(FROZEN/'CONTINUATION_PAIRS.json',bank/'pairs.json')
    plan={'experiment':'E15','section':105,'source_files':source_hashes(),'pair_commit':'0d0a5a96',
        'registration_commit':'1095e4e973b618cbf40f5f4f3c2d8d4bca33dc31','features':list(PAIRS),
        'test_items':672,'base_reference_dev_items':672,'labels_sha256':P.sha(labels),
        'values':{f:specs[f]['values'] for f in PAIRS},'W1_activation_seal_sha256':P.sha(K.W1/'ANALYSIS_SEAL.json'),
        'W1_activation_manifest_sha256':P.sha(K.W1/'activations.json'),'W1_full_items_sha256':P.sha(P.ROOT/'cache/g_agreement/blindspot/w1-bank/items.DO_NOT_STAGE.jsonl'),
        'W1_donor_input_sha256':P.sha(w1_inputs/'items.input.jsonl'),
        'donors':'Random: newly frozen value-independent hash from W1 same test row/cluster/length bin, self allowed. Extra W1 mismatch: exact original opposite-value donor_id. Not relabelled as random.',
        'reference':'Base-Qwen actual text tokens, no adapter, no question, no bullet; dev only.',
        'oracle':'Unmodified native Oracle prompt; prefix=- ; summed candidate likelihoods at44.',
        'nla':'DESCRIPTIVE; native prompt at42, continuation prefix empty, off native explanation mode.',
        'validity':'Per-pair base dev AUROC>=0.80, no sign flips. Average only valid pairs on test; no valid pairs=>NOT EVALUABLE. All pairs retained in report.',
        'science_cap_seconds':1800,'setup_seconds':1500,'seed':20261023,'bootstrap':2000}
    P.dump(bank/'plan.json',plan)
    names=['items.input.jsonl','reference.input.jsonl','acts42.npy','acts44.npy','pairs.json','plan.json']
    P.seal(bank,names,'E15_FROZEN_BEFORE_ANY_REFERENCE_OR_READER_SCORING')
    for n in ('plan.json','INPUT_SEAL.json'):shutil.copyfile(bank/n,FROZEN/n)
    return bank


def native_score(name,obj,h,pairs):
    if name=='olens':return obj.paired_logodds_templates(h,44,pairs,prefix='- ')
    from mats.readers.nla import paired_logodds_templates
    return paired_logodds_templates(obj,h,pairs,prefix='',batch=32)


def valid_pairs(dev_aurocs):
    return [j for j,v in enumerate(dev_aurocs) if v is not None and math.isfinite(v) and v>=.80]


def base_score(ol,items,pairs):
    """Base text plus candidates; right padding and exact predictive positions."""
    import torch
    columns=[];device=next(ol.model.parameters()).device
    with ol.base(),torch.no_grad():
        for a,b in pairs:
            candidates=[ol.tok.encode(s,add_special_tokens=False) for s in (a,b)]
            if len(candidates[0])!=len(candidates[1]):raise ValueError('candidate token mismatch')
            k=len(candidates[0]);seqs=[x['ids']+c for x in items for c in candidates]
            lengths=torch.tensor([len(x['ids']) for x in items for _ in candidates],device=device)
            n=max(map(len,seqs));ids=torch.full((len(seqs),n),ol.tok.pad_token_id or 0,dtype=torch.long,device=device);mask=torch.zeros_like(ids)
            for j,s in enumerate(seqs):ids[j,:len(s)]=torch.tensor(s,device=device);mask[j,:len(s)]=1
            positions=lengths[:,None]-1+torch.arange(k,device=device)[None,:]
            keep=torch.unique(positions,sorted=True)
            output=ol.model(input_ids=ids,attention_mask=mask,logits_to_keep=keep,use_cache=False)
            rows=torch.arange(len(seqs),device=device)[:,None]
            logits=output.logits[rows,torch.searchsorted(keep,positions)].float()
            targets=ids.gather(1,positions+1)
            values=torch.log_softmax(logits,-1).gather(-1,targets[:,:,None]).squeeze(-1).sum(1).reshape(-1,2)
            columns.append((values[:,0]-values[:,1]).cpu())
    return torch.stack(columns)


def run(a):
    import torch
    P.verify(a.bank,'INPUT_SEAL.json');R._labels_absent(a.bank)
    plan=json.loads((a.bank/'plan.json').read_text());assignment=json.loads(a.assignment.read_text())
    if (assignment.get('issuer')!='integrator' or assignment.get('experiment')!='E15' or not assignment.get('pod_id') or
        assignment['pod_id']!=os.environ.get('RUNPOD_POD_ID') or assignment.get('source_files')!=plan['source_files'] or
        assignment.get('plan_sha256')!=P.sha(a.bank/'plan.json') or assignment.get('previous_gpu_seconds')!=0 or
        assignment.get('science_cap_gpu_seconds')!=CAP or assignment.get('staging_allowance_seconds')!=1500 or
        any(assignment.get(k) is not True for k in ('brief_registered','brief_pushed','manifest_committed','external_hardstop_verified'))):
        raise ValueError('exact E15 integrator assignment required')
    for name,h in plan['source_files'].items():
        if P.sha(P.ROOT/name)!=h:raise ValueError('exact archived source required: '+name)
    created=float(assignment['provider_created_epoch']);absolute=float(assignment['deadline_epoch'])-180
    if not 0<float(assignment['deadline_epoch'])-created<=float(assignment['allocated_gpu_seconds']):raise ValueError('custody mismatch')
    end=min(created+1500,absolute)
    if not created<=time.time()<end:raise ValueError('setup expired')
    a.out.mkdir(parents=True,exist_ok=False);first=None
    def expired(*_):raise TimeoutError('E15 first-science/setup/absolute deadline')
    def check():
        if time.time()>=end:expired()
        signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()))
    old=signal.signal(signal.SIGALRM,expired);check()
    try:
        items=P.rows(a.bank/'items.input.jsonl');reference=P.rows(a.bank/'reference.input.jsonl')
        if len(items)!=672 or len(reference)!=672:raise ValueError('full8-row scope required')
        pairs={f:[(p['A'],p['B']) for p in s['pairs']] for f,s in json.loads((a.bank/'pairs.json').read_text())['rows'].items()}
        arrays={site:torch.from_numpy(np.load(a.bank/f'acts{site}.npy',allow_pickle=False)) for site in (42,44)}
        if any(h.ndim!=2 or len(h)!=672 or not torch.isfinite(h).all() for h in arrays.values()):raise ValueError('invalid sealed activation arrays')
        assets=R._assets(a.assets,names=('model','olens','nla'));ol=R._load_oracle(assets)
        from mats.readers.nla import load_nla
        nla=load_nla(root=assets['nla'],load_ar=False,enable_thinking=False)
        groups={f:[i for i,x in enumerate(items) if x['feature']==f] for f in PAIRS}
        refs={f:[x for x in reference if x['feature']==f] for f in PAIRS}
        def unit(f,name,indices=None):
            check()
            if name=='base':return base_score(ol,(indices if indices is not None else refs[f][:16]),pairs[f])
            idx=groups[f][:16] if indices is None else indices
            return native_score(name,ol if name=='olens' else nla,arrays[44 if name=='olens' else 42][idx],pairs[f])
        f=next(iter(PAIRS))
        for name in ('base','olens','nla'):unit(f,name)
        torch.cuda.synchronize();check();first=time.time();end=min(first+CAP,absolute)
        with (a.out/'EXPERIMENT_CLOCK.json').open('x') as s:json.dump({'first_science_epoch':first,'experiment':'E15'},s)
        timings=[];remaining=0.
        for f in PAIRS:
            for name in ('base','olens','nla'):
                times=[]
                for _ in range(3):
                    check();torch.cuda.synchronize();start=time.perf_counter();unit(f,name);torch.cuda.synchronize();times.append(time.perf_counter()-start)
                remaining+=statistics.median(times)*math.ceil(84/16)
                timings.append({'feature':f,'reader':name,'warmed_units_s':times})
        F=time.time()-first+remaining;allocation=min(1.5*F+360,CAP);end=min(end,first+allocation)
        fits=math.isfinite(F) and F>0 and F<=allocation and time.time()+remaining<=end
        P.dump(a.out/'FORECAST.json',{'status':'FIT' if fits else 'NO_FIT','forecast_s':F,'allocation_s':allocation,'timings':timings,'timing_outputs_used':False})
        if not fits:P.dump(a.out/'STATUS.json',{'status':'NO_FIT','scope_reduced':False});return
        records=[];scoremap={}
        for f in PAIRS:
            for name in ('base','olens','nla'):
                selected=refs[f] if name=='base' else groups[f]
                for start in range(0,len(selected),16):
                    subset=selected[start:start+16];values=unit(f,name,subset)
                    if tuple(values.shape)!=(2,len(subset)) or not torch.isfinite(values).all():raise ValueError('invalid paired scores')
                    for j,it in enumerate(subset):
                        x=it if name=='base' else items[it]
                        r={'id':x['id'],'feature':f,'reader':name,'layer':None if name=='base' else 44 if name=='olens' else 42,
                            'arm':'true','scores':values[:,j].tolist(),'status':'COMPLETE'}
                        records.append(r);scoremap[x['id'],name]=r
                        with (a.out/'scores.partial.jsonl').open('a') as s:s.write(json.dumps(r,sort_keys=True)+'\n');s.flush()
        for x in items:
            for name in ('olens','nla'):
                for arm,key in (('random_donor','random_donor_id'),('w1_mismatched','w1_mismatched_donor_id')):
                    donor=scoremap[x[key],name]
                    records.append({**donor,'id':x['id'],'feature':x['feature'],'arm':arm,'donor_id':x[key]})
        if len(records)!=4704:raise ValueError('incomplete full E15 grid')
        check();P.jsonl(a.out/'scores.jsonl',records)
        P.dump(a.out/'provenance.json',{'input_seal_sha256':P.sha(a.bank/'INPUT_SEAL.json'),'source_files':plan['source_files'],
            'no_new_activation_capture':True,'base_reference_dev_only':True,'pair_commit':plan['pair_commit'],'assignment_sha256':P.sha(a.assignment)})
        check();P.dump(a.out/'SCORE_SEAL.json',{'status':'E15_SCORES_SEALED_BEFORE_DEV_VALIDITY_AND_TEST_LABEL_JOIN',
            'files':{n:P.sha(a.out/n) for n in ('scores.jsonl','provenance.json','FORECAST.json','EXPERIMENT_CLOCK.json')}})
    except Exception as exc:
        P.dump(a.out/'FAILURE.json',{'status':'INCOMPLETE','error_type':type(exc).__name__,'reason':str(exc),'no_automatic_retry':True});raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        if first is not None:P.dump(a.out/'SCIENCE_RECEIPT.json',{'first_science_epoch':first,'completed_epoch':time.time(),'elapsed_s':time.time()-first,'effective_deadline_epoch':end,'cap_seconds':CAP})


def analyse(bank,outputs,labels,out):
    from dataclasses import asdict
    from mats import metrics
    bank,outputs,labels,out=map(Path,(bank,outputs,labels,out))
    if out.exists():raise ValueError('analysis exists; no repeat')
    P.verify(bank,'INPUT_SEAL.json');P.verify(outputs,'SCORE_SEAL.json')
    plan=json.loads((bank/'plan.json').read_text());provenance=json.loads((outputs/'provenance.json').read_text())
    if provenance['input_seal_sha256']!=P.sha(bank/'INPUT_SEAL.json') or provenance['source_files']!=plan['source_files']:
        raise ValueError('source/input lineage mismatch')
    for n,h in plan['source_files'].items():
        if P.sha(P.ROOT/n)!=h:raise ValueError('use exact frozen E15 source: '+n)
    items=P.rows(bank/'items.input.jsonl');refs=P.rows(bank/'reference.input.jsonl');raw=P.rows(outputs/'scores.jsonl')
    expected={(x['id'],'base','true') for x in refs}|{(x['id'],name,arm) for x in items for name in ('olens','nla') for arm in ('true','random_donor','w1_mismatched')}
    keys=[(r['id'],r['reader'],r['arm']) for r in raw]
    if len(keys)!=len(set(keys)) or set(keys)!=expected or any(r['status']!='COMPLETE' or len(r['scores'])!=2 or not np.isfinite(r['scores']).all() for r in raw):
        raise ValueError('incomplete/nonfinite E15 score grid')
    if P.sha(labels)!=plan['labels_sha256']:raise ValueError('frozen label mismatch')
    labelrows=P.rows(labels);lookup={r['id']:r for r in labelrows};ids={x['id'] for x in items+refs}
    if len(lookup)!=len(labelrows) or set(lookup)!=ids:raise ValueError('label scope mismatch')
    lock=out.with_name(out.name+'.lock.json');lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as stream:json.dump({'status':'STARTED','score_seal_sha256':P.sha(outputs/'SCORE_SEAL.json')},stream)
    scoremap=dict(zip(keys,raw));rows=[]
    for feature in PAIRS:
        refids=[x['id'] for x in refs if x['feature']==feature];testids=[x['id'] for x in items if x['feature']==feature]
        if any(lookup[i]['split']!='dev' for i in refids) or any(lookup[i]['split']!='test' for i in testids):raise ValueError('split mismatch')
        target=plan['values'][feature][0];dy=np.array([lookup[i]['value']==target for i in refids]);y=np.array([lookup[i]['value']==target for i in testids]);groups=np.array([lookup[i]['cluster'] for i in testids])
        dev=np.array([scoremap[i,'base','true']['scores'] for i in refids]);dev_aucs=[metrics.auroc_labels(dev[:,j],dy) for j in range(2)];valid=valid_pairs(dev_aucs)
        row={'feature':feature,'base_dev_pair_auroc':dev_aucs,'valid_pairs':valid,'n_dev':len(refids),'n_test':len(testids),'status':'EVALUABLE' if valid else 'NOT EVALUABLE','readers':{}}
        for name in ('olens','nla'):
            matrices={arm:np.array([scoremap[i,name,arm]['scores'] for i in testids]) for arm in ('true','random_donor','w1_mismatched')}
            reader={'status':'PRIMARY' if name=='olens' else 'DESCRIPTIVE_OFF_NATIVE',
                'all_pairs_descriptive':[asdict(metrics.auroc_ci(matrices['true'][:,j],y,groups,n_boot=2000,seed=P.SEED)) for j in range(2)]}
            if valid:
                scores={arm:m[:,valid].mean(1) for arm,m in matrices.items()}
                reader['arms']={arm:asdict(metrics.auroc_ci(s,y,groups,n_boot=2000,seed=P.SEED)) for arm,s in scores.items()}
                s,d=scores['true'],scores['random_donor']
                reader['true_minus_random_donor']={'difference':metrics.auroc_labels(s,y)-metrics.auroc_labels(d,y),
                    'ci95':list(metrics.cluster_bootstrap(lambda j:metrics.auroc_labels(s[j],y[j])-metrics.auroc_labels(d[j],y[j]),groups,n_boot=2000,seed=P.SEED))}
            row['readers'][name]=reader
        rows.append(row)
    eligible=[r for r in rows if r['valid_pairs']]
    summary={'n_valid_rows':len(eligible),'oracle_at_most_060':sum(r['readers']['olens']['arms']['true']['auroc']<=.60 for r in eligible),
        'oracle_at_least_075':sum(r['readers']['olens']['arms']['true']['auroc']>=.75 for r in eligible),
        'status':'NOT EVALUABLE' if not eligible else 'DESCRIPTIVE: report counts; no formal global decision threshold specified'}
    out.mkdir(parents=True,exist_ok=False)
    P.dump(out/'metrics.json',{'experiment':'E15','rows':rows,'summary':summary,'score_seal_sha256':P.sha(outputs/'SCORE_SEAL.json'),'labels_sha256':P.sha(labels)})
    (out/'RESULTS.md').write_text('Prediction (§105): On dev-valid rows Oracle native-mode continuation AUROC stays≤0.60 on most rows.\n\n'+json.dumps(summary,indent=2)+'\n\nAll pairs, failed validity gates, signed scores, native/off-native status and donor controls are reported in metrics.json.\n')
    P.dump(out/'ANALYSIS_SEAL.json',{'status':'E15_ANALYSIS_COMPLETE','files':{n:P.sha(out/n) for n in ('metrics.json','RESULTS.md')}})
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True);s.add_parser('prepare');r=s.add_parser('run')
    for n in ('bank','assignment','assets','out'):r.add_argument('--'+n,type=Path,required=True)
    t=s.add_parser('analyse')
    for n in ('bank','outputs','labels','out'):t.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.command=='prepare':print(prepare())
    elif a.command=='run':
        with P.logged('e15_native_continuation_scoring',gpu=True,extra={'cap_seconds':CAP}):run(a)
    else:print(json.dumps(analyse(a.bank,a.outputs,a.labels,a.out),indent=2))
