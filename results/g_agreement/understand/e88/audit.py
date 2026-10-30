"""E88 independent CPU audit. Never modifies or invokes a source bank analysis."""
import argparse, hashlib, json, math, os, subprocess, time, unicodedata
from collections import defaultdict
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CACHE=ROOT/'cache/g_agreement/understand/e88'
SEED=20261028
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def normalize(s):return ' '.join(unicodedata.normalize('NFKC',s).casefold().split())
def signed(j,label):
    if j.get('category')=='UNPARSEABLE':return None
    if j.get('category')!='states_value':return 0
    v=j['values'];correct='A' if label==1 else 'B'
    return 1 if v==[correct] else -1 if len(v)==1 else 0
def rate(values):
    x=np.asarray(values,float)
    if x.ndim!=1 or not len(x) or not np.isin(x,[-1,0,1]).all():raise ValueError('single readout/item signed grid required')
    rng=np.random.default_rng(SEED)
    boot=np.concatenate([x[rng.integers(len(x),size=(min(100,2000-i),len(x)))].mean(1) for i in range(0,2000,100)])
    ci=np.quantile(boot,[.025,.975]).tolist();s=float(x.mean())
    return dict(S=s,CI95=ci,n=len(x),verdict='REPORTED' if s>=.2 and ci[0]>0 else 'MISSED')
def bounds(records):
    grouped=defaultdict(list)
    for x in records:grouped[(x['bank'],x['reader'],x['row'])].append(x)
    out=[]
    for key,xs in sorted(grouped.items()):
        if len({x['item_id'] for x in xs})!=len(xs):raise ValueError('duplicate row/item; cluster adapter required')
        vals=[x['score'] for x in xs];lo=rate([-1 if v is None else v for v in vals]);hi=rate([1 if v is None else v for v in vals])
        kept=[v for v in vals if v is not None]
        out.append(dict(bank=key[0],reader=key[1],row=key[2],n=len(xs),unparseable=sum(v is None for v in vals),parseable=rate(kept) if kept else None,lower=lo,upper=hi,verdict_can_flip=lo['verdict']!=hi['verdict']))
    return out
def kappa(a,b):
    if len(a)!=len(b) or not a:raise ValueError('paired labels required')
    labels=set(a)|set(b);po=sum(x==y for x,y in zip(a,b))/len(a)
    pe=sum(a.count(k)*b.count(k) for k in labels)/len(a)**2
    return dict(n=len(a),agreement=po,kappa=None if pe==1 else (po-pe)/(1-pe))
def compare_judges(records):
    by=defaultdict(list)
    for x in records:by[(x['bank'],x['reader'],x['row'])].append(x)
    pairs=[x for x in records if x['primary_score'] is not None and x['new_score'] is not None]
    out={'agreement':kappa([x['primary_code'] for x in pairs],[x['new_code'] for x in pairs]) if pairs else None,'unparseable_pairs':len(records)-len(pairs),'rows':[]}
    for key,xs in sorted(by.items()):
        good=[x for x in xs if x['primary_score'] is not None and x['new_score'] is not None]
        out['rows'].append(dict(bank=key[0],reader=key[1],row=key[2],matched_parseable=len(good),old=rate([x['primary_score'] for x in good]) if good else None,new=rate([x['new_score'] for x in good]) if good else None,scope='matched judged sample; full-row flip requires full row coverage'))
    return out
def audit_tokens(xs):
    from tokenizers import Tokenizer
    pin=read(ROOT/'results/g_agreement/understand/e52/BASIS_INPUTS_2026-10-27.json')['files']['tokenizer']
    if sha(pin['path'])!=pin['sha256']:raise ValueError('tokenizer hash')
    tok=Tokenizer.from_file(pin['path']);out=[]
    for x in xs:
        ids=tok.encode(x['text'],add_special_tokens=False).ids
        idx=x['registered_index'];observed=x.get('capture_index')
        declared=x['ids'];same=ids==declared
        out.append(dict(bank=x['bank'],item_id=x['item_id'],registered_index=idx,capture_index=observed,capture_index_proof=x.get('capture_index_proof'),token_id=declared[idx] if 0<=idx<len(declared) else None,decoded=tok.decode([declared[idx]],skip_special_tokens=False) if 0<=idx<len(declared) else None,encoded_ids_match=same,capture_index_matches=None if observed is None else observed==idx,status='PASS' if same and observed==idx else 'FAIL' if not same or observed is not None else 'CAPTURE_INDEX_NOT_BOUND'))
    return out
def run(planpath,part,continue_before_statistics=False):
    planpath=Path(planpath).resolve();rel=str(planpath.relative_to(ROOT))
    if subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)!=planpath.read_bytes():raise ValueError('plan must be committed')
    p=read(planpath)
    for f,h in p['sources'].items():
        if sha(f)!=h:raise ValueError('source changed: '+f)
    for f,h in p['code'].items():
        if sha(HERE/f)!=h:raise ValueError('audit code changed')
    data=read(p['data']['path'])
    if sha(p['data']['path'])!=p['data']['sha256']:raise ValueError('private input hash')
    dest=HERE/('cpu_once' if part=='cpu' else 'judging_'+part+'_once');marker=CACHE/(part+'_ONCE.json')
    CACHE.mkdir(parents=True,exist_ok=True)
    if continue_before_statistics:
        repair=read(HERE/'PRESTAT_SCHEMA_REPAIR.json')
        if part!='cpu' or list(dest.iterdir()) or sha(marker)!=repair['original_claim_sha256']:raise ValueError('pre-statistics continuation custody')
        if read(marker)['plan_sha256']!=repair['original_plan_sha256'] or sha(planpath)!=repair['continuation_plan_sha256']:raise ValueError('continuation plan binding')
        write(CACHE/'PRESTAT_CONTINUATION_ONCE.json',dict(status='SAME_CLAIM_OPERATIONAL_CONTINUATION_NEVER_RESET',repair_sha256=sha(HERE/'PRESTAT_SCHEMA_REPAIR.json')))
    else:
        dest.mkdir(exist_ok=False)
        write(marker,dict(status='CLAIMED_NEVER_RESET',plan_sha256=sha(planpath),part=part,started_epoch=time.time()))
    start=time.time()
    if part=='cpu':
        import sys
        sys.path.insert(0,str(ROOT.parent/'wt-wmech/results/g_agreement/understand/e49/job'))
        import statements49
        signed_records=[]
        for x in data['raw_signed_records']:
            if x.get('regex'):
                category=statements49.categorize(x['row'],x['text'],x['label'])
                score={'correct_only':1,'wrong_only':-1,'both':0,'neither':0}[category]
            else:score=signed(x['judgment'],x['label'])
            signed_records.append({k:x[k]for k in ['bank','reader','row','item_id']}|dict(score=score))
        result=dict(experiment='E88',scope='items1-4 and frozen judging inventories',probe_audit=data['probes'],low_probes=[x for x in data['probes']if x['AUROC']<.5],unparseable_bounds=bounds(signed_records),read_token_audit=audit_tokens(data['token_sample']),coverage=data['coverage'],judging_pending=data['judging_pending'])
        counts=defaultdict(lambda:dict(total=0,UNPARSEABLE=0))
        for x in data['e67_terminal_status']:
            g=counts[str(x['wave'])+'|'+x['reader']+'|'+x['condition']];g['total']+=1;g['UNPARSEABLE']+=int(x['status']=='UNPARSEABLE')
        result['E67_terminal_counts']=dict(counts)
        result['leakage']=[]
        import struct
        exe=CACHE/'near_duplicate'
        subprocess.run(['clang++','-O3','-std=c++17',str(HERE/'near_duplicate.cpp'),'-o',str(exe)],check=True)
        for bank,items in sorted(data['items'].items()):
            dev=[x for x in items if x['split']=='dev'];test=[x for x in items if x['split']=='test']
            inp=CACHE/(bank+'_distance_input.private.bin');pairs=CACHE/(bank+'_near_pairs.private.tsv')
            with inp.open('wb') as f:
                f.write(struct.pack('<II',len(dev),len(test)))
                for x in dev+test:
                    s=normalize(x['text']);v=[ord(c) for c in s];f.write(struct.pack('<I',len(v)));f.write(struct.pack('<'+'I'*len(v),*v))
            subprocess.run([str(exe),str(inp),str(pairs)],check=True)
            near=[line.split() for line in pairs.read_text().splitlines()];devhit={int(x[0]) for x in near};testhit={int(x[1]) for x in near}
            result['leakage'].append(dict(bank=bank,dev=len(dev),test=len(test),comparisons=len(dev)*len(test),near_pairs=len(near),dev_items_with_near=len(devhit),test_items_with_near=len(testhit),criterion='NFKC + casefold + collapsed whitespace; Levenshtein/max Unicode codepoint length <0.1',private_pair_sha256=sha(pairs)))
    else:result=compare_judges(data['comparisons'])
    result.update(cpu_only=True,GPU_hours=0,wall_seconds=time.time()-start,plan_sha256=sha(planpath),sealed_source_verdicts_unchanged=True)
    write(dest/'RESULTS.json',result)
    write(dest/'RESULT_SEAL.json',dict(experiment='E88',part=part,files={'RESULTS.json':sha(dest/'RESULTS.json')},plan_sha256=sha(planpath),claim_sha256=sha(marker)))
    print(json.dumps(dict(part=part,wall_seconds=result['wall_seconds'],seal_sha256=sha(dest/'RESULT_SEAL.json'))))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--plan',required=True);a.add_argument('--part',choices=['cpu','5','6'],required=True);a.add_argument('--continue-before-statistics',action='store_true');args=a.parse_args();run(args.plan,args.part,args.continue_before_statistics)
