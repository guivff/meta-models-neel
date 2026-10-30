"""E56/E57 CPU-only J-lens readouts and frozen E52 J labels, once per bank."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
import time
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
E52=ROOT/'results/g_agreement/understand/e52'
sys.path.insert(0,str(E52))
from build_basis import sha,read,dump,CACHE as E52_CACHE
from run_labels import verify,FullRankReader
from sparse_primary import fraction,primary_label
import core

def committed(path):
    path=Path(path).resolve();rel=str(path.relative_to(ROOT))
    if subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)!=path.read_bytes():raise ValueError('input plan must be committed before scoring')

def sealed_ref(ref,seal):
    p=Path(ref['path']).resolve();s=Path(seal['path']).resolve()
    if sha(s)!=seal['sha256'] or sha(p)!=ref['sha256']:raise ValueError('input bytes differ')
    if (s.parent/ref['member']).resolve()!=p or read(s)['files'][ref['member']]!=ref['sha256']:raise ValueError('input file absent from supplied seal')
    return p

def ranks_and_hits(logits,side_ids,groups):
    """Item-specific frozen tokens; top50 retained for E57 capacity_list."""
    import torch
    if len(side_ids)!=len(logits) or len(groups)!=len(logits):raise ValueError('per-item token coverage')
    top=logits.topk(50,dim=1).indices.cpu().numpy();ranks=[];descriptive=[]
    for i,(pair,sets) in enumerate(zip(side_ids,groups)):
        rr=[]
        for ids in pair:
            if not ids:rr.append(None);continue
            if any(type(t)!=int or t<0 or t>=logits.shape[1] for t in ids):raise ValueError('invalid token id')
            best=logits[i,ids].max();rr.append(int((logits[i]>best).sum()))
        ranks.append(rr);g={}
        for name,entries in sets.items():
            matched10=[];matched50=[];best=[]
            for e in entries:
                ids=e['token_ids']
                if not ids or any(type(t)!=int or t<0 or t>=logits.shape[1] for t in ids):raise ValueError('invalid descriptive token set')
                matched10.append(bool(np.isin(top[i,:10],ids).any()));matched50.append(bool(np.isin(top[i],ids).any()))
                best.append(int((logits[i]>logits[i,ids].max()).sum()))
            g[name]={'entry_names':[e['name'] for e in entries],'best_full_vocab_ranks':best,'top10_present':matched10,'top50_present':matched50,'distinct_entries_top10':sum(matched10),'distinct_entries_top50':sum(matched50)}
        descriptive.append(g)
    return ranks,top,descriptive

class Reader(FullRankReader):
    def score_items(self,acts,side_ids,groups):
        import torch
        ranks=[];top=[];desc=[]
        with torch.no_grad():
            for start in range(0,len(acts),16):
                h=torch.tensor(np.asarray(acts[start:start+16]),dtype=torch.float32,device='cpu')
                z=self.norm((h@self.j.T).to(torch.bfloat16)).float();logits=z@self.wu.T
                if not torch.isfinite(logits).all():raise ValueError('nonfinite CPU J-lens readout')
                r,t,d=ranks_and_hits(logits,side_ids[start:start+16],groups[start:start+16]);ranks+=r;top.extend(t);desc+=d
        return ranks,np.asarray(top),desc

def validate_units(units,records,order):
    if len({u['id'] for u in units})!=len(units) or any(not re.fullmatch(r'[A-Za-z0-9_-]+',u['id']) for u in units):raise ValueError('unique safe frozen unit ids required')
    tests={r['id']:r for r in records if r['split']=='test'}
    if len(tests)!=sum(r['split']=='test' for r in records) or len(set(order))!=len(order):raise ValueError('duplicate test/capture ids')
    seen=set()
    for u in units:
        ids=u['item_ids']
        if not ids or len(set(ids))!=len(ids) or seen.intersection(ids) or not set(ids)<=set(tests) or not set(ids)<=set(order):raise ValueError('unique test-only units required')
        if any(tests[i]['feature']!=u['source_row'] for i in ids):raise ValueError('source row mismatch')
        if set(u['value_token_ids'])!=set(ids) or set(u['descriptive_token_sets'])!=set(ids):raise ValueError('all token sets frozen per item')
        if any(len(u['value_token_ids'][i])!=2 for i in ids):raise ValueError('exactly A/B token sets required')
        if u['binary']:
            y=[tests[i]['label'] for i in ids]
            if len(y)!=84 or set(y)!={0,1} or sum(y)!=42:raise ValueError('84 balanced A=1/B=0 test items required')
        seen.update(ids)
    if seen!=set(tests):raise ValueError('all frozen test items must be represented')
    return tests

def run(bank):
    planpath=HERE/(bank+'_INPUT_PLAN.json')
    if not planpath.exists():print(bank+' WAITING_FOR_COMMITTED_BANK_CAPTURE_AND_VALUE_SETS');return 2
    verify(ROOT,read(HERE/'CODE_SEAL_2026-10-27.json')['files']);committed(planpath);plan=read(planpath)
    if plan['experiment']!=bank or plan['layer']!=44 or plan['split']!='test':raise ValueError('registered bank/layer/split required')
    for ref in plan['value_sources']:
        if sha(ref['path'])!=ref['sha256']:raise ValueError('frozen value definitions differ')
    records=read(sealed_ref(plan['records'],plan['bank_seal']));order=read(sealed_ref(plan['order'],plan['capture_seal']))
    ap=sealed_ref(plan['activations'],plan['capture_seal']);acts=np.load(ap,allow_pickle=False,mmap_mode='r')
    if acts.shape!=(len(order),5120):raise ValueError('block44 capture shape')
    tests=validate_units(plan['units'],records,order);indices={k:i for i,k in enumerate(order)}
    basis=read(E52/'BASIS_SEAL_2026-10-27.json');verify(E52_CACHE,basis['files'])
    sp=E52_CACHE/'sparse-primary';null=read(sp/'NULL_SEAL.json');verify(sp,null['files']);verify(sp,read(sp/'ATOM_SEAL.json')['files'])
    primary=read(E52/'primary/E36/ROW_LABELS.json')
    if primary['atom_seal_sha256']!=sha(sp/'ATOM_SEAL.json') or primary['null_seal_sha256']!=sha(sp/'NULL_SEAL.json'):raise ValueError('E52 sparse binding differs')
    if read(E52/'primary/E36/R1_SANITY.json')['met'] is not True:raise ValueError('registered J-label sanity failed')
    cache=ROOT/'cache/g_agreement/understand'/bank.lower()/'jlens';cache.mkdir(parents=True,exist_ok=True)
    with (cache/'ONCE.json').open('x') as f:json.dump({'status':'CLAIMED_NEVER_RESET','created_epoch':time.time(),'plan_sha256':sha(planpath)},f)
    out=cache/'raw';out.mkdir(exist_ok=False)
    import torch
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.jspace import nn_pursuit
    reader=Reader();atoms=torch.load(sp/'atoms.pt',map_location='cpu',weights_only=True)['atoms']
    q=np.load(E52_CACHE/'basis_L44_r1536.npy',allow_pickle=False);svdnull=read(E52_CACHE/'ENRICHMENT_NULL.json')['ranks']
    from tokenizers import Tokenizer
    tok=Tokenizer.from_file(read(E52/'BASIS_INPUTS_2026-10-27.json')['files']['tokenizer']['path'])
    rows=[];started=time.time()
    for u in plan['units']:
        ids=u['item_ids'];h=np.array(acts[[indices[i] for i in ids]])
        pair=[u['value_token_ids'][i] for i in ids];groups=[u['descriptive_token_sets'][i] for i in ids]
        ranks,top,desc=reader.score_items(h,pair,groups)
        dump(out/(u['id']+'.readout.json'),{'items':[{'id':i,'best_full_vocab_ranks':r,'top10_token_ids':t[:10].tolist(),'top50_token_ids':t.tolist(),'top10_tokens':[tok.decode([int(x)]) for x in t[:10]],'top50_tokens':[tok.decode([int(x)]) for x in t],'descriptive':d} for i,r,t,d in zip(ids,ranks,top,desc)]})
        row={'bank':bank,'row':u['id'],'source_row':u['source_row'],'condition':u.get('condition'),'n_test':len(ids)}
        if u['binary']:
            y=np.array([tests[i]['label'] for i in ids]);enrich,means,d,norm=core.enrich(h,y,q,svdnull)
            g3=core.g3(np.array(ranks,dtype=np.int64),y) if all(all(x is not None for x in r) for r in ranks) else {'status':'NOT EVALUABLE','readable':None,'reason':'empty frozen value-token sets'}
            hh=np.asarray(d,dtype=np.float32)[None,:];idx,coef,rec=nn_pursuit(torch.from_numpy(hh),atoms,k=16);value=float(fraction(hh,rec.numpy())[0])
            label=primary_label(value,null['median'],null['percentile97_5'],g3)
            row.update(label=label,J_fraction=value,J_readability=g3,enrichment=enrich,secondary_SVD_label=core.label(enrich,g3),class_mean_difference_norm=norm)
            np.savez_compressed(out/(u['id']+'.direction.npz'),class_means=means,direction=d,indices=idx.numpy(),coefficients=coef.numpy(),reconstruction=rec.numpy())
        else:row.update(label='NOT APPLICABLE',J_fraction=None,J_readability={'status':'NOT EVALUABLE','reason':'non-binary descriptive unit; no registered A/B direction','readable':None})
        rows.append(row);print(bank+' '+u['id']+' '+row['label'],flush=True)
    dump(out/'RAW_SEAL.json',{'files':{p.name:sha(p) for p in out.iterdir()}})
    dest=HERE/(bank+'_results');dest.mkdir(exist_ok=False)
    dump(dest/'ROW_LABELS.json',{'experiment':bank,'label_role':'PRIMARY_SPARSE','rows':rows,'plan_sha256':sha(planpath),'code_seal_sha256':sha(HERE/'CODE_SEAL_2026-10-27.json'),'raw_seal_sha256':sha(out/'RAW_SEAL.json'),'raw_directory':str(out),'GPU_hours':0,'wall_seconds':time.time()-started,'reader_outcomes_accessed':False})
    (dest/'LABELS.md').write_text('# '+bank+' J labels\n\n| Unit | Primary label |\n|---|---|\n'+'\n'.join('| '+r['row']+' | '+r['label']+' |' for r in rows)+'\n')
    dump(dest/'LABEL_SEAL.json',{'files':{p.name:sha(p) for p in dest.iterdir()}})
    return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('bank',choices=['E56','E57']);args=parser.parse_args();raise SystemExit(run(args.bank))
