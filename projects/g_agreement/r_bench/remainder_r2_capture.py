"""Remainder R2 isolated native reader taps. CPU preflight/mock; guarded live capture.

Every full run is gated by the same-code, same-manifest, same-pod live smoke and
original guard (1,200 seconds standalone; explicit joint warm run: 5,400 seconds). No allocation, downloads in CPU phases, or API calls.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np
from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench import remainder_r2 as A

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'cache/g_agreement/r'
OUT = SOURCE/'remainder/r2'
RESULTS = ROOT/'results/g_agreement/r/remainder/r2'
READERS = {'olens': 44, 'nla': 42}
TAPS = (20, 32, 40)
CONDITIONS = ('natural', 'shuf')
POSITIONS = ('pre_answer',)
SEED, CAP, RESERVE = 20261020, 1200, 300


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.partial')
    tmp.write_text(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n');tmp.replace(path)


def code_hash():
    paths=[Path(__file__),ROOT/'projects/g_agreement/r_bench/collect.py',ROOT/'projects/g_agreement/r_bench/beyond_text.py',
           *[ROOT/f'projects/g_agreement/core/{x}.py' for x in ('config','model','readers','scoring_lo')]]
    return digest({str(p.relative_to(ROOT)):sha(p) for p in paths})


def provenance(pod):
    p=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
    git=p.stdout.strip() or os.environ.get('R_GIT_SHA') or ((ROOT/'GIT_SHA').read_text().strip() if (ROOT/'GIT_SHA').exists() else '')
    if not git: raise ValueError('Missing git SHA')
    return {'pod':pod,'git_sha':git,'code_sha':code_hash(),'created_at':datetime.now(timezone.utc).isoformat()}


def read_jsonl(path):
    with Path(path).open() as f:
        return [json.loads(l) for l in f if l.strip()]


def label_rows(source):
    out={};files={}
    for pattern,field in [('model_labels*.jsonl','model_label'),('re_relabel*.jsonl','label')]:
        for p in sorted(source.glob(pattern)):
            files[str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)]=sha(p)
            for row in read_jsonl(p):
                key=(row['dataset'],row['item_id']); value=row.get(field)
                if key in out and out[key]['label']!=value: raise ValueError(f'Conflicting model-derived label: {key}')
                out[key]={'label':value,'source_key':row['key'],'source_path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
                          'source_pod':row.get('pod'),'source_git_sha':row.get('git_sha'),'greedy_text':row.get('greedy_text')}
    return out,files


def resolve_label(item,keys):
    it=json.loads(json.dumps(item));ds=it['dataset']
    needs=it['primary'].get('label_source')=='model' or ds in ('re_internal_refuse','re_internal_abstain')
    if not needs: return it,{'kind':'construction'}
    rec=keys.get((ds,it['item_id']))
    if rec is None: raise ValueError(f'Missing model-derived key: {ds}/{it["item_id"]}')
    if rec['label'] not in (0,1,None): raise ValueError('Invalid model-derived label')
    it['label']=rec['label']
    it['primary']['key']='greedy'
    if it['label'] is not None:
        it['primary']['answer']=it['primary']['candidates'][0 if it['label'] else 1]
    return it,{'kind':'model',**{k:v for k,v in rec.items() if k!='greedy_text'}}


def derangement(ids,key):
    if len(ids)<2: raise ValueError('Fewer than two states in a within-fact/split shuffle')
    seed=int(hashlib.sha256(f'{SEED}|{key}'.encode()).hexdigest()[:16],16)
    rng=np.random.default_rng(seed); order=rng.permutation(len(ids)); perm=np.empty(len(ids),int)
    perm[order]=np.roll(order,1)
    return dict(zip(ids,[ids[i] for i in perm]))


def eligibility_problem(group):
    counts=Counter(it['split'] for it in group)
    if any(counts[split]<2 for split in ('pool','test')):
        return 'No usable pool/test split for registered pool-trained probe'
    if any(it['primary'].get('sided')=='kway' for it in group):
        return 'K-way fact has no registered binary AUROC/native-score mapping; multiclass redesign required'
    return None


def make_manifest(root=ROOT,source=SOURCE):
    defects=A.defects_from_source(root/'projects/g_agreement/r_bench/interim.py')
    keys,key_files=label_rows(source);facts=[];errors=[];unavailable=[];banks={};files={**key_files}
    frozen=json.loads((root/'projects/g_agreement/manifest/frozen_config_r.json').read_text())
    for bank,filename in A.BANKS.items():
        p=root/'projects/g_agreement/dataset'/filename;bsha=sha(p)
        if frozen['items_sha256'].get(filename)!=bsha: errors.append(f'{filename}: frozen bank hash mismatch')
        data=json.loads(p.read_text());data=data['items'] if isinstance(data,dict) else data
        banks[bank]={'file':str(p.relative_to(root)),'sha256':bsha}
        groups=defaultdict(list)
        for it in data:
            if it['dataset'] not in defects and it['split'] in ('pool','test'): groups[it['dataset']].append(it)
        for ds,group in sorted(groups.items()):
            counts=Counter(it['split'] for it in group)
            problem=eligibility_problem(group)
            if problem:
                unavailable.append({'bank':bank,'dataset':ds,'reason':problem,'split_counts':dict(counts)})
                continue
            ip=source/'states'/ds/'index.json'
            if not ip.exists(): errors.append(f'{ds}: missing index');continue
            index=json.loads(ip.read_text());ids=index['item_ids'];lookup={v:i for i,v in enumerate(ids)}
            if len(ids)!=len(lookup): raise ValueError(f'{ds}: duplicate source index')
            if 'chat' not in index.get('renders',[]): errors.append(f'{ds}: source index lacks chat render')
            if len(index.get('splits',[]))!=len(ids): errors.append(f'{ds}: source index lacks split mapping')
            state_files={}
            for layer in READERS.values():
                sp=source/'states'/ds/f'chat_L{layer}.npy'
                if not sp.exists():errors.append(f'{ds}: missing chat_L{layer}');continue
                x=np.load(sp,mmap_mode='r',allow_pickle=False)
                if x.shape!=(len(ids),C.D_MODEL):errors.append(f'{ds}: invalid state shape {x.shape}')
                elif not np.isfinite(x).all():errors.append(f'{ds}: nonfinite state')
                state_files[str(layer)]={'path':str(sp.relative_to(root)),'sha256':sha(sp),'shape':list(x.shape)}
            items=[]
            for it in sorted(group,key=lambda x:(x['split'],x['item_id'])):
                iid=it['item_id']
                if iid not in lookup: errors.append(f'{ds}: missing item state {iid}');continue
                j=lookup[iid]
                if index.get('splits',[None]*len(ids))[j]!=it['split']:errors.append(f'{ds}: split mismatch {iid}')
                try: resolved,label_info=resolve_label(it,keys)
                except ValueError as e:errors.append(str(e));continue
                items.append({'item_id':iid,'split':it['split'],'label':resolved['label'],'state_row':j,
                              'item_sha256':digest(it),'label_info':label_info,'item':resolved})
            for split in ('pool','test'):
                subset=[r for r in items if r['split']==split]
                if len(subset)<2:errors.append(f'{ds}: fewer than two {split} items');continue
                donor=derangement([r['item_id'] for r in subset],f'{ds}|{split}')
                for r in subset:r.update(donor_item_id=donor[r['item_id']],donor_state_row=lookup[donor[r['item_id']]])
            facts.append({'bank':bank,'dataset':ds,'tag':group[0]['tag'],'index_path':str(ip.relative_to(root)),
                          'index_sha256':sha(ip),'states':state_files,'items':items})
    n=sum(len(f['items']) for f in facts)
    return {'schema':2,'banks':banks,'key_files':files,'facts':facts,'unavailable_facts':unavailable,'errors':errors,'readers':READERS,'taps':TAPS,
            'conditions':CONDITIONS,'seed':SEED,'items':n,'expected_score_rows':4*n,
            'minimum_tap_bytes':n*4*len(TAPS)*len(POSITIONS)*C.D_MODEL*2,
            'positions':POSITIONS,'dtype':'float16','note':'One pre-answer vector per item; Phase-R item families each register one template. Extra templates fail. Null keys remain null.'}


def compact_size_estimate(manifest,batch=32):
    """Deterministic shape estimate plus conservative JSON/fit-output allowances."""
    from projects.g_agreement.r_bench import collect as K
    from projects.g_agreement.core import scoring_lo as L
    template_counts=Counter(len(L.templates_for(K.family_for(r['item']['primary']))) for f in manifest['facts'] for r in f['items'])
    if set(template_counts)!={1}:raise ValueError('Unexpected multi-template family; do not shrink silently')
    chunks=sum(len(READERS)*len(CONDITIONS)*((sum(r['split']==split for r in f['items'])+batch//2-1)//(batch//2)) for f in manifest['facts'] for split in ('pool','test'))
    payload=manifest['items']*len(READERS)*len(CONDITIONS)*len(TAPS)*C.D_MODEL*2
    # Source-specific item metadata is included in the full capture input manifest.
    manifest_bytes=len(json.dumps(manifest,indent=2,sort_keys=True).encode())+1
    meta={'pod':'p'*80,'git_sha':'g'*40,'code_sha':'c'*64,'created_at':'t'*40}
    score_allowance=0;index_allowance=0
    def nbytes(obj,indent=None):return len(json.dumps(obj,sort_keys=bool(indent),indent=indent).encode())+1
    for f in manifest['facts']:
      for reader,layer in READERS.items():
       for split in ('pool','test'):
        rows=[r for r in f['items'] if r['split']==split]
        for condition in CONDITIONS:
         for start in range(0,len(rows),max(1,batch//2)):
          chunk=rows[start:start+max(1,batch//2)]
          for r in chunk:
            obj={**meta,'reader':reader,'bank':f['bank'],'dataset':f['dataset'],'tag':f['tag'],'split':split,'condition':condition,'read_layer':layer,
                 'item_id':r['item_id'],'label':r['label'],'label_info':r['label_info'],'native_score':-1.7976931348623157e308,
                 'source_item_id':r['item_id'] if condition=='natural' else r['donor_item_id'],'source_row':r['state_row'] if condition=='natural' else r['donor_state_row'],
                 'source_sha256':f['states'][str(layer)]['sha256'],'bank_sha256':manifest['banks'][f['bank']]['sha256'],'manifest_sha256':'m'*64}
            score_allowance+=nbytes(obj)+32
          idx={'reader':reader,'bank':f['bank'],'dataset':f['dataset'],'split':split,'condition':condition,'read_layer':layer,'tap_blocks':TAPS,'positions':POSITIONS,
               'item_ids':[r['item_id'] for r in chunk],'arrays':{str(k):{'sha256':'h'*64,'shape':[len(chunk),C.D_MODEL]} for k in TAPS},
               'scores_sha256':'h'*64,'manifest_sha256':'m'*64,'hook':{'answer_indices':[],'T':1,'position':'pre_answer','layout':'N,d','dtype':'float16'},
               'adapter':C.OLENS_REPO if reader=='olens' else C.NLA_REPO,'checkpoint':C.OLENS_SHA if reader=='olens' else C.NLA_SHA,**meta}
          index_allowance+=nbytes(idx,2)+128
    header_bytes=chunks*len(TAPS)*128
    result_allowance=2_000_000_000
    total=payload+header_bytes+manifest_bytes+score_allowance+index_allowance+result_allowance
    return {'items':manifest['items'],'facts':len(manifest['facts']),'readers':len(READERS),'conditions':len(CONDITIONS),'blocks':list(TAPS),'position':'pre_answer','dtype':'float16','hidden_width':C.D_MODEL,
            'templates_per_item':dict(template_counts),'state_array_bytes':payload,'state_array_GB':payload/1e9,'state_array_GiB':payload/2**30,'npy_header_bytes':header_bytes,
            'capture_manifest_bytes':manifest_bytes,'score_json_allowance_bytes':score_allowance,'index_json_allowance_bytes':index_allowance,'compact_probe_package_allowance_bytes':result_allowance,
            'conservative_total_bytes':total,'conservative_total_GB':total/1e9,'limit_bytes':15_000_000_000,'within_limit':total<=15_000_000_000,
            'note':'Metadata serialized from frozen IDs and exact output schema, padded for 80-character pod IDs, float formatting and headers; includes 2 GB probe package allowance, not measured outcomes. Includes two readers, both controls, pool+test. No full states leave network volume.'}


def smoke_selection(manifest):
    chosen={}
    for bank in A.BANKS:
        candidates=[f for f in manifest['facts'] if f['bank']==bank]
        if not candidates:raise ValueError(f'SMOKE FAILED: missing {bank}')
        # Selection depends only on frozen labels/IDs, never reader scores.
        fact=next((f for f in candidates if all(sum(r['split']==s for r in f['items'])>=2 for s in ('pool','test'))),None)
        if fact is None:raise ValueError(f'SMOKE FAILED: missing {bank}/pool/test')
        chosen[fact['dataset']]={s:[r['item_id'] for r in fact['items'] if r['split']==s][:2] for s in ('pool','test')}
    return chosen


def validate_guard(record,pod,deadline,now,joint_run=False):
    if joint_run:
        from projects.g_agreement.r_bench.remainder_joint import validate_joint_guard
        return validate_joint_guard(record,pod,deadline,now)
    values=[record.get('started_epoch'),record.get('deadline_epoch'),deadline,now]
    if any(isinstance(x,bool) or not isinstance(x,(float,int)) or not np.isfinite(x) for x in values):raise ValueError('Invalid guard epochs')
    start,hard,deadline,now=values
    if record.get('pod')!=pod or record.get('experiment')!='r2':raise ValueError('Wrong guard pod/experiment')
    if start>now or not 0<hard-start<=CAP:raise ValueError('Original R2 guard exceeds cap')
    if deadline>hard:raise ValueError('Deadline renewal refused')
    if deadline-now<=RESERVE:raise ValueError('Pull reserve reached')


def guards(pod,guard_dir,deadline,joint_run=False):
    if joint_run:
        from projects.g_agreement.r_bench.remainder_joint import guard,validate_joint_guard
        result=guard(pod,Path(guard_dir))
        validate_joint_guard(result,pod,deadline,time.time())
        return {"guard_dir":str(Path(guard_dir).resolve()),"guard_sha256":result["guard_sha256"],"deadline_epoch":deadline,"joint_run":True}
    own=[x.split(b'=',1)[1].decode() for x in Path('/proc/1/environ').read_bytes().split(b'\0') if x.startswith(b'RUNPOD_POD_ID=')]
    if own!=[pod]:raise ValueError('POD ID MISMATCH')
    g=Path(guard_dir);p=g/'guard.json';record=json.loads(p.read_text());validate_guard(record,pod,deadline,time.time())
    if not (g/'ARMED').exists():raise ValueError('Shared guards unarmed')
    for name in ('watchdog','hardstop'):
        log=(g/f'{name}.log').read_text()
        if 'armed:' not in log or pod not in log:raise ValueError(f'{name} not armed for pod')
        os.kill(int((g/f'{name}.pid').read_text()),0)
    return {'guard_dir':str(g.resolve()),'guard_sha256':sha(p),'deadline_epoch':deadline}


def validate_arrays(arrays,n):
    if set(arrays)!=set(TAPS):raise ValueError('SMOKE FAILED: missing reader tap block')
    for layer,x in arrays.items():
        if x.shape!=(n,C.D_MODEL) or x.dtype!=np.float16:raise ValueError(f'Invalid compact fp16 tap shape at {layer}: {x.shape}')
        if not np.isfinite(x).all():raise ValueError(f'Nonfinite read-position state at {layer}')


class ReadPositionHook:
    """Capture only the shared pre-answer row on device, never a sequence window."""
    def __init__(self,reader,layers,read_layer):
        from projects.g_agreement.r_bench import collect as K
        self.base=K.ReaderStateHook(reader,layers,read_layer)
        self.layers=layers;self.forwards={k:[] for k in layers};self.handles=[]
    def __enter__(self):
        from projects.g_agreement.core import model as M
        import torch
        for layer in self.layers:
            def hook(_m,_i,out,layer=layer):
                h=out[0] if isinstance(out,tuple) else out
                if h.shape[1]<=self.base.head_len:raise ValueError('Missing teacher-forced read position')
                self.forwards[layer].append(h[:,self.base.head_len-1,:].detach().to(torch.float16).cpu())
            self.handles.append(M.blocks(self.base.model)[layer].register_forward_hook(hook))
        return self
    def __exit__(self,*args):
        for handle in self.handles:handle.remove()
        self.handles=[]
    def assemble(self,pairs,batch,groups):
        import torch
        plan=[]
        for fam,indices in groups:
            if len(self.base.templates_for(fam))!=1:raise ValueError('Compact capture requires one frozen template per item')
            plan.extend(indices[i:i+max(1,batch//2)] for i in range(0,len(indices),max(1,batch//2)))
        arrays={}
        for layer,forwards in self.forwards.items():
            if len(forwards)!=len(plan):raise ValueError('Read-position forward count mismatch')
            x=torch.empty((len(pairs),C.D_MODEL),dtype=torch.float16)
            for ids,hidden in zip(plan,forwards):
                if hidden.shape!=(2*len(ids),C.D_MODEL):raise ValueError('Read-position row count mismatch')
                if not torch.equal(hidden[0::2],hidden[1::2]):raise ValueError('Candidate-dependent pre-answer state')
                x[ids]=hidden[0::2]
            arrays[layer]=x
        return arrays,[],{'T':1,'position':'pre_answer','layout':'N,d','dtype':'float16'}


def native_value(row,item):
    if item['primary'].get('sided')=='kway':raise ValueError('K-way native score is outside registered binary AUROC design')
    key='lp_A' if item['primary'].get('sided')=='one' else 'lo'
    x=row.get(key)
    if x is None or not np.isfinite(x):raise ValueError('Native verbalizer score missing/nonfinite')
    return float(x)


def score_chunk(reader,H,items,layer,batch):
    from projects.g_agreement.r_bench import collect as K
    with ReadPositionHook(reader,TAPS,layer) as hook:
        scores,groups=K.score_items(reader,H,items,layer,batch=batch,return_groups=True)
    pairs=[K.item_pair(K.base_name(reader),it['primary']) for it in items]
    arrays,answer_indices,meta=hook.assemble(pairs,batch=batch,groups=groups)
    arrays={k:v.numpy() if hasattr(v,'numpy') else np.asarray(v) for k,v in arrays.items()}
    validate_arrays(arrays,len(items))
    if len(scores)!=len(items):raise ValueError('Native scores/state row mismatch')
    return scores,arrays,{'answer_indices':answer_indices,**meta}


def expected_keys(manifest,smoke=False):
    selection=smoke_selection(manifest) if smoke else None;expected=set()
    for f in manifest['facts']:
        for r in f['items']:
            if smoke and r['item_id'] not in selection.get(f['dataset'],{}).get(r['split'],[]):continue
            for reader in READERS:
                for condition in CONDITIONS:expected.add((reader,f['dataset'],r['split'],condition,r['item_id']))
    return expected


def audit(root,manifest,smoke=False):
    expected=expected_keys(manifest,smoke);seen=set();arms=[];manifest_sha=digest(manifest)
    lookup={(f['dataset'],r['item_id']):(f,r) for f in manifest['facts'] for r in f['items']}
    for index_number,p in enumerate(sorted(Path(root).rglob('index.json'))):
        idx=json.loads(p.read_text());rows=read_jsonl(p.parent/'scores.jsonl')
        if idx['manifest_sha256']!=manifest_sha:raise ValueError('Capture manifest mismatch')
        arrays={k:np.load(p.parent/f'tap{k}.npy',mmap_mode='r',allow_pickle=False) for k in TAPS}
        validate_arrays(arrays,len(rows))
        if idx['item_ids']!=[r['item_id'] for r in rows]:raise ValueError('State/score index mismatch')
        if idx.get('positions')!=list(POSITIONS) or idx.get('tap_blocks')!=list(TAPS):raise ValueError('Tap convention mismatch')
        for layer,x in arrays.items():
            if list(x.shape)!=idx['arrays'][str(layer)]['shape'] or sha(p.parent/f'tap{layer}.npy')!=idx['arrays'][str(layer)]['sha256']:raise ValueError('Tap checksum mismatch')
        if sha(p.parent/'scores.jsonl')!=idx['scores_sha256']:raise ValueError('Score checksum mismatch')
        for r in rows:
            k=tuple(r[x] for x in ('reader','dataset','split','condition','item_id'))
            if k in seen:raise ValueError('Duplicate capture key')
            if any(not r.get(x) or r[x]!=idx.get(x) for x in ('pod','git_sha','code_sha')):raise ValueError('Missing or mismatched provenance')
            if r.get('manifest_sha256')!=manifest_sha:raise ValueError('Score manifest mismatch')
            fact,it=lookup.get((r['dataset'],r['item_id']),(None,None))
            if fact is None or r['reader'] not in READERS or r['condition'] not in CONDITIONS:raise ValueError('Unregistered row')
            donor=r['condition']=='shuf';layer=READERS[r['reader']]
            checks={'bank':fact['bank'],'tag':fact['tag'],'split':it['split'],'label':it['label'],'read_layer':layer,
                    'source_item_id':it['donor_item_id'] if donor else it['item_id'],
                    'source_row':it['donor_state_row'] if donor else it['state_row'],
                    'source_sha256':fact['states'][str(layer)]['sha256'],'bank_sha256':manifest['banks'][fact['bank']]['sha256']}
            if any(r.get(key)!=value for key,value in checks.items()):raise ValueError('Score/key/state mapping mismatch')
            if not isinstance(r.get('native_score'),(int,float)) or not np.isfinite(r['native_score']):raise ValueError('Native score nonfinite')
            seen.add(k)
        if index_number%256==0:print(json.dumps({'phase':'capture-audit','verified_chunks':index_number+1}),flush=True)
        arms.extend(dict(reader=idx['reader'],bank=idx['bank'],split=idx['split'],condition=idx['condition'],tap_block=k,n_rows=len(rows)) for k in TAPS)
    if seen!=expected:raise ValueError(f'SMOKE FAILED: missing {len(expected-seen)} keys, extra {len(seen-expected)} keys')
    contract=A.capture_smoke_contract();A.assert_arm_coverage(arms,set(map(tuple,contract['expected_cells'])),tuple(contract['dimensions']))
    return {'score_rows':len(seen),'arm_cells':72,'status':'PASS','files':len(list(Path(root).rglob('index.json')))}


def throughput_gate(cert,manifest,meta,guard,batch,now=None):
    for key,value in {'manifest_sha256':digest(manifest),'pod':meta['pod'],'git_sha':meta['git_sha'],'code_sha':meta['code_sha'],'batch':batch,**guard}.items():
        if cert.get(key)!=value:raise ValueError(f'Live smoke certificate mismatch: {key}')
    if cert.get('kind')!='live' or cert.get('coverage',{}).get('arm_cells')!=72:raise ValueError('Real 72-cell live smoke required')
    remaining=guard['deadline_epoch']-(time.time() if now is None else now)
    rate=cert.get('measured_pull_bytes_per_second',0)
    if not isinstance(rate,(int,float)) or not np.isfinite(rate) or rate<=0:raise ValueError('BUDGET BLOCKED: measured Mac pull bandwidth required for full raw-tap transfer')
    pull=max(RESERVE,1.5*cert['projected_tap_bytes']/rate)
    if guard.get('joint_run'):
        from projects.g_agreement.r_bench.remainder_joint import checkpoint_budget
        pull=checkpoint_budget(cert,rate)['capture_reserve_seconds']
    if cert['projected_full_seconds']+pull>remaining:raise ValueError(f'BUDGET BLOCKED: projected {cert["projected_full_seconds"]:.1f}s + {pull:.1f}s measured pull reserve > {remaining:.1f}s remaining; no silent downsample')
    return {'pull_reserve_seconds':pull,'model_load_seconds':cert.get('load_seconds',{})}


def capture(manifest,root,meta,smoke,batch,deadline,readers=None,mock=False,pull_reserve=RESERVE,load_estimates=None):
    from projects.g_agreement.r_bench import collect as K
    from projects.g_agreement.core import model as M,readers as R
    if Path(root).exists():raise ValueError('Refuse existing capture output; distinct smoke/full directories required')
    selection=smoke_selection(manifest) if smoke else None;rates=defaultdict(list);loads={};bytes_per_row=defaultdict(list);began=time.monotonic();manifest_sha=digest(manifest);used_sources={};source_validation_seconds=0.;source_bytes_hashed=0;written_tap_bytes=0
    for name,layer in READERS.items():
        if deadline is not None and time.time()+pull_reserve+1.5*(load_estimates or {}).get(name,0)>=deadline:
            raise RuntimeError('Pull reserve reached before model load; partial evidence retained')
        target=None;t0=time.monotonic()
        if not mock:
            if name=='olens':target=M.load_target();reader=R.OLensReader().bind(target)
            else:reader=R.NLAReader().bind()
        loads[name]=time.monotonic()-t0
        try:
            for fact in manifest['facts']:
                if smoke and fact['dataset'] not in selection:continue
                source_ref=fact['states'][str(layer)];source_path=ROOT/source_ref['path']
                t_source=time.monotonic()
                if sha(source_path)!=source_ref['sha256']:raise ValueError('Source state changed before capture: '+source_ref['path'])
                source_validation_seconds+=time.monotonic()-t_source;source_bytes_hashed+=source_path.stat().st_size
                used_sources[str(source_path)]=source_ref['sha256']
                source=np.load(source_path,mmap_mode='r',allow_pickle=False)
                for split in ('pool','test'):
                    rows=[r for r in fact['items'] if r['split']==split and (not smoke or r['item_id'] in selection[fact['dataset']][split])]
                    for condition in CONDITIONS:
                        for start in range(0,len(rows),max(1,batch//2)):
                            if deadline is not None and time.time()+pull_reserve>=deadline:raise RuntimeError('Pull reserve reached; partial evidence retained')
                            chunk=rows[start:start+max(1,batch//2)];items=[r['item'] for r in chunk]
                            H=np.asarray(source[[r['state_row' if condition=='natural' else 'donor_state_row'] for r in chunk]],dtype=np.float32)
                            t0=time.monotonic()
                            if mock:
                                scores=[{'lo':float(i%2),'lp_A':float(i%2)} for i in range(len(chunk))]
                                arrays={k:H.astype(np.float16) for k in TAPS};hookmeta={}
                            else:scores,arrays,hookmeta=score_chunk(reader,H,items,layer,batch)
                            bytes_per_row[name].append(sum(x.nbytes for x in arrays.values())/len(chunk))
                            dst=Path(root)/name/fact['dataset']/split/condition/f'chunk{start:07d}';dst.mkdir(parents=True)
                            stamped=[]
                            for r,s in zip(chunk,scores):
                                stamped.append({**meta,'reader':name,'bank':fact['bank'],'dataset':fact['dataset'],'tag':fact['tag'],'split':split,
                                    'condition':condition,'read_layer':layer,'item_id':r['item_id'],'label':r['label'],'label_info':r['label_info'],
                                    'native_score':native_value(s,r['item']),'source_item_id':r['item_id'] if condition=='natural' else r['donor_item_id'],
                                    'source_row':r['state_row'] if condition=='natural' else r['donor_state_row'],'source_sha256':fact['states'][str(layer)]['sha256'],
                                    'bank_sha256':manifest['banks'][fact['bank']]['sha256'],'manifest_sha256':manifest_sha})
                            (dst/'scores.jsonl').write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in stamped))
                            hashes={}
                            for k,x in arrays.items():
                                np.save(dst/f'tap{k}.npy',x);written_tap_bytes+=(dst/f'tap{k}.npy').stat().st_size
                                hashes[str(k)]={'sha256':sha(dst/f'tap{k}.npy'),'shape':list(x.shape)}
                            save(dst/'index.json',{'reader':name,'bank':fact['bank'],'dataset':fact['dataset'],'split':split,'condition':condition,
                                 'read_layer':layer,'tap_blocks':TAPS,'positions':POSITIONS,'item_ids':[r['item_id'] for r in chunk],
                                 'arrays':hashes,'scores_sha256':sha(dst/'scores.jsonl'),'manifest_sha256':manifest_sha,'hook':hookmeta,
                                 'adapter':C.OLENS_REPO if name=='olens' else C.NLA_REPO,
                                 'checkpoint':C.OLENS_SHA if name=='olens' else C.NLA_SHA,**meta})
                            elapsed=time.monotonic()-t0;rates[name].append(elapsed/len(chunk))
                            print(json.dumps({'reader':name,'dataset':fact['dataset'],'split':split,'condition':condition,'start':start,'rows':len(chunk),'seconds':elapsed}),flush=True)
        finally:
            if not mock:
                if target is not None:M.unload(target)
                else:reader.unload()
    for path,expected_sha in used_sources.items():
        if deadline is not None and time.time()+pull_reserve>=deadline:raise RuntimeError('Pull reserve reached before source audit')
        t_source=time.monotonic()
        if sha(path)!=expected_sha:raise ValueError('Source state changed during capture: '+path)
        source_validation_seconds+=time.monotonic()-t_source;source_bytes_hashed+=Path(path).stat().st_size
    if deadline is not None and time.time()+pull_reserve>=deadline:raise RuntimeError('Pull reserve reached before output audit')
    audit_start=time.monotonic();coverage=audit(root,manifest,smoke);audit_seconds=time.monotonic()-audit_start
    projected_bytes=sum(max(bytes_per_row[r])*manifest['items']*len(CONDITIONS) for r in READERS)
    full_source_bytes=2*sum((ROOT/st['path']).stat().st_size for f in manifest['facts'] for st in f['states'].values())
    audit_projection=audit_seconds*projected_bytes/max(1,written_tap_bytes)
    source_projection=source_validation_seconds*full_source_bytes/max(1,source_bytes_hashed)
    projection=1.5*(sum(loads.values())+sum(max(rates[r])*manifest['items']*len(CONDITIONS) for r in READERS)+audit_projection+source_projection)
    return {'coverage':coverage,'rates_seconds_per_item':dict(rates),'load_seconds':loads,'projected_full_seconds':projection,'wall_seconds':time.monotonic()-began,'projected_tap_bytes':projected_bytes,'pull_reserve_seconds':pull_reserve,'audit_seconds':audit_seconds,
            'projected_audit_seconds':audit_projection,'projected_source_validation_seconds':source_projection,'chunk_timing_includes_io':True}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=('size','preflight','mock-smoke','live-smoke','capture','audit'),required=True)
    p.add_argument('--pod',default='mac-cpu');p.add_argument('--guard-dir',type=Path);p.add_argument('--deadline-epoch',type=float);p.add_argument('--batch',type=int,default=32);p.add_argument('--measured-pull-bytes-per-second',type=float,default=0)
    p.add_argument("--joint-run",action="store_true",help="Use explicit original warm R2/R6 joint guard; no per-phase cap reset")
    a=p.parse_args(argv)
    if a.batch<2:raise ValueError('batch >=2 required')
    if a.phase=='size':
        manifest=make_manifest();result={**compact_size_estimate(manifest,a.batch),**provenance(a.pod)};save(RESULTS/'compact_size.json',result);print(json.dumps(result));return 0 if result['within_limit'] else 2
    manifest=make_manifest();OUT.mkdir(parents=True,exist_ok=True);meta=provenance(a.pod)
    save(RESULTS/'capture_preflight.json',{'facts':len(manifest['facts']),'items':manifest['items'],'expected_score_rows':manifest['expected_score_rows'],
         'minimum_tap_bytes':manifest['minimum_tap_bytes'],'unavailable_facts':manifest['unavailable_facts'],'errors':manifest['errors'],'manifest_sha256':digest(manifest),**meta})
    if manifest['errors']:raise ValueError('PREFLIGHT FAILED: '+ '; '.join(manifest['errors'][:15]))
    mp=OUT/'capture_manifest.json'
    if mp.exists() and digest(json.loads(mp.read_text()))!=digest(manifest):raise ValueError('Frozen capture manifest changed; explicit amendment required')
    save(mp,manifest)
    if a.phase=='preflight':
        estimate=compact_size_estimate(manifest,a.batch);save(RESULTS/'compact_size.json',{**estimate,**meta})
        if not estimate['within_limit']:raise ValueError('Compact output estimate exceeds 15 GB; stop and wait')
        print(json.dumps({'status':'PASS','facts':len(manifest['facts']),'score_rows':manifest['expected_score_rows'],'minimum_tap_GiB':manifest['minimum_tap_bytes']/2**30,'conservative_output_GB':estimate['conservative_total_GB']}));return 0
    if a.phase=='audit':print(json.dumps(audit(OUT/'capture',manifest)));return 0
    if a.phase=='mock-smoke':
        result=capture(manifest,OUT/'capture_mock',meta,True,a.batch,None,mock=True);save(RESULTS/'capture_mock_smoke.json',{'kind':'mock',**result,**meta});return 0
    if a.pod=='mac-cpu' or a.guard_dir is None or a.deadline_epoch is None:p.error('Live phases require explicit pod, guard-dir, deadline-epoch')
    guard=guards(a.pod,a.guard_dir,a.deadline_epoch,a.joint_run);smoke=a.phase=='live-smoke'
    gate={'pull_reserve_seconds':RESERVE,'model_load_seconds':{}}
    if not smoke:gate=throughput_gate(json.loads((OUT/'live_smoke.json').read_text()),manifest,meta,guard,a.batch)
    result=capture(manifest,OUT/('capture_smoke' if smoke else 'capture'),meta,smoke,a.batch,a.deadline_epoch,
                   pull_reserve=gate['pull_reserve_seconds'],load_estimates=gate['model_load_seconds'])
    cert={'kind':'live','measured_pull_bytes_per_second':a.measured_pull_bytes_per_second,'phase':a.phase,'manifest_sha256':digest(manifest),'batch':a.batch,**meta,**guard,**result}
    save(OUT/('live_smoke.json' if smoke else 'capture_complete.json'),cert)
    save(RESULTS/('capture_live_smoke.json' if smoke else 'capture_complete.json'),cert)
    if smoke:throughput_gate(cert,manifest,meta,guard,a.batch)
    return 0


if __name__=='__main__':raise SystemExit(main())
