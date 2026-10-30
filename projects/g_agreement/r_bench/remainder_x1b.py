"""X1b-lite design/CPU preparation. No model imports, downloads or outcome selection."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import os
import sys
import uuid
from contextlib import contextmanager
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'results/g_agreement/r/remainder/x1b'
DATA_REL = Path('cache/g_agreement/r/remainder/x1b')
CACHE = ROOT/DATA_REL
BANK = ROOT/'projects/g_agreement/dataset/items_re.json'
SEED = 20261020
LAYERS = (24, 28)
ARMS = ('bridge_patch', 'answer_patch', 'random_bridge', 'natural', 'random_answer')
READERS = {'olens': (44,), 'nla': (42,), 'jlens': (28, 42), 'skip_a': (42,)}
PILOT_N = 20
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")+"-"+uuid.uuid4().hex
RUN_KIND = "test" if "pytest" in sys.modules else "real"


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def save(path,x):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.partial');tmp.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n');tmp.replace(path)


def read(path):return json.loads(Path(path).read_text())


def provenance(pod='mac-cpu'):
    from projects.g_agreement.r_bench.collect import git_sha
    files=sorted(Path(__file__).parent.glob('remainder_x1b*.py')) + [Path(__file__).parent/'remainder_x1_analyze.py', Path(__file__).parent/'remainder_x1.py']
    code_hash=digest({p.name:sha(p) for p in files})
    return {'pod':pod,'git_sha':git_sha(),'code_sha':code_hash,'code_sha256':code_hash,'run_id':RUN_ID,'run_kind':RUN_KIND,
            'created_at':datetime.now(timezone.utc).isoformat()}


def rank(*keys):return digest([SEED,*keys])


def records(path=BANK):
    blob=read(path);items=blob['items'] if isinstance(blob,dict) else blob
    answers={r['prompt_text']:r for r in items if r['dataset']=='re_khop2_answer'}
    result=[]
    for r in items:
        if r['dataset']!='re_khop2_bridge':continue
        a=answers.get(r['prompt_text']);c=r['construction']
        if a is None or a['split']!=r['split']:raise ValueError('Bridge/answer bank join differs')
        if 'LABEL_DEFECT' in (r.get('tag'),a.get('tag')):continue
        result.append({'id':r['item_id'],'split':r['split'],'text':r['prompt_text'],'position':r['read_position'],
                       **{k:c[k] for k in ('template','hop1','hop2','bridge','answer','bridge_jlens')}})
    ids=[r['id'] for r in result]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate item IDs')
    return sorted(result,key=lambda r:r['id'])


def pair_candidates(rec,bank):
    return sorted([x['id'] for x in bank if x['split']==rec['split'] and x['template']==rec['template']
                   and x['bridge']!=rec['bridge'] and x['answer']!=rec['answer']],key=lambda k:rank(rec['id'],k))


def unrelated(rec,donor,bank):
    return sorted([x['id'] for x in bank if x['split']=='pool' and x['hop2']!=rec['hop2']
                   and x['bridge'] not in (rec['bridge'],donor['bridge'])],key=lambda k:rank(rec['id'],donor['id'],'random',k))


def prepare(path=BANK):
    from . import remainder_x1 as old
    plan=old.prepare(path)
    plan.update(experiment='X1b-lite',caliper=None,norm_matching='exact natural vectors; pool-fitted state-norm-ratio deciles; no hard caliper',status='SECTION_34_CONFIRMED_WAITING_POD',section=34)
    plan.pop('cm_fit_ids')
    for pair in plan['pairs']:pair.pop('class_mean_supported_donors')
    return plan


def ratio_geometry(rec,donor,states,layer,site):
    a=np.asarray(states[rec][layer][site],dtype=np.float64);b=np.asarray(states[donor][layer][site],dtype=np.float64)
    na=float(np.linalg.norm(a));nb=float(np.linalg.norm(b));delta=float(np.linalg.norm(b-a))
    if not np.isfinite([na,nb,delta]).all() or na<=0:raise ValueError('Invalid norm ratio '+rec+' '+donor+' '+site)
    return {'ratio':nb/na,'norm':delta,'relative_delta':delta/na}


def decile(ratio,cuts):
    cuts=np.asarray(cuts,float)
    if cuts.shape!=(9,) or not np.isfinite(cuts).all() or np.any(np.diff(cuts)<0):raise ValueError('Invalid decile boundaries '+repr(cuts.tolist()))
    if not np.isfinite(ratio):raise ValueError('Invalid ratio '+str(ratio))
    return int(np.searchsorted(cuts,ratio,side='left'))


def fit_deciles(plan,states,layer):
    pool=[r for r in plan['records'] if r['split']=='pool'];result={}
    for site in ('bridge','answer'):
        values=[]
        for r in pool:
            donors=pair_candidates(r,plan['records'])
            if donors:values.append(ratio_geometry(r['id'],donors[0],states,layer,site)['ratio'])
        if len(values)!=len(pool):raise ValueError('Pool nominal donor coverage incomplete')
        result[site]=np.quantile(values,np.arange(1,10)/10,method='linear').tolist()
    return result


def match_control(rec,donor,random_ids,states,layer,site,cuts):
    geometry=ratio_geometry(rec,donor,states,layer,site);bin_id=decile(geometry['ratio'],cuts)
    candidates=[{'donor':k,**ratio_geometry(rec,k,states,layer,site)} for k in random_ids]
    eligible=[x for x in candidates if decile(x['ratio'],cuts)==bin_id]
    chosen=min(eligible,key=lambda x:rank(rec,donor,site,x['donor'])) if eligible else None
    return {'real':geometry,'decile':bin_id,'control':chosen,'candidates':candidates,'status':'MATCHED' if chosen else 'UNMATCHED_DECILE'}


def freeze_pairs(plan,states,layer,split):
    bank={r['id']:r for r in plan['records']};cuts=fit_deciles(plan,states,layer);out=[];excluded=[];meta=provenance()
    for p in plan['pairs']:
        if p['split']!=split:continue
        rec=bank[p['recipient']];did=p['nominal_donor']
        if did is None:excluded.append({**p,'reason':'NO_NOMINAL_DONOR'});continue
        if did!=pair_candidates(rec,plan['records'])[0]:raise ValueError('Changed nominal donor '+did)
        random_ids=unrelated(rec,bank[did],plan['records'])
        matches={site:match_control(rec['id'],did,random_ids,states,layer,site,cuts[site]) for site in ('bridge','answer')}
        out.append({**p,**meta,'donor':did,'layer':layer,'status':'FROZEN','norm':matches['bridge']['real']['norm'],
                    'answer_norm':matches['answer']['real']['norm'],'random_bridge':matches['bridge']['control'],
                    'random_answer':matches['answer']['control'],'matches':matches,'decile_boundaries':cuts})
    return out,excluded


def select_layer(pilot,eligible_test_counts):
    """Only pool rows. Prefer L24 if projected F>=80 and N>=40; else max minimum quota fraction."""
    scored={}
    for layer in LAYERS:
        rows=[r for r in pilot if r['layer']==layer]
        if any(r.get('split')!='pilot' for r in rows):raise ValueError('Layer selection must use pool pilot only')
        if len(rows)!=PILOT_N or len({r['recipient'] for r in rows})!=PILOT_N:raise ValueError('Need all 20 pool pilot rows at each layer')
        f=sum(r['natural_lo']>0 and r['patched_lo']<0 for r in rows)/PILOT_N
        n=sum(r['natural_lo']>0 and r['patched_lo']>=0 for r in rows)/PILOT_N
        count=eligible_test_counts[layer];scored[layer]={'expected_F':f*count,'expected_N':n*count,'quota_score':min(f*count/80,n*count/40)}
    chosen=24 if scored[24]['quota_score']>=1 else max(LAYERS,key=lambda L:(scored[L]['quota_score'],-L))
    return {'primary_layer':chosen,'pilot_projection':scored,'underpowered_projection':scored[chosen]['quota_score']<1,'selection_uses_test_outcomes':False}


class Mahalanobis:
    """Pool-only ridge covariance, exact low-rank inverse, including orthogonal residual energy."""
    def __init__(self,fit):
        x=np.asarray(fit,dtype=np.float64)
        if x.ndim!=2 or len(x)<3 or not np.isfinite(x).all():raise ValueError('Invalid natural pool states')
        self.mean=x.mean(0);z=(x-self.mean)/np.sqrt(len(x)-1)
        gram=z@z.T;values,u=np.linalg.eigh(gram);keep=values>max(1e-12,values.max()*1e-12)
        self.values=values[keep];self.axes=(u[:,keep].T@z)/np.sqrt(self.values[:,None])
        self.ridge=.01*float(np.sum(z*z))/x.shape[1]
        if self.ridge<=0:raise ValueError('Degenerate pool covariance')
    def score(self,x):
        z=np.asarray(x,dtype=np.float64)-self.mean;proj=z@self.axes.T
        return np.maximum(0,((z*z).sum(1)-(proj*proj*(self.values/(self.values+self.ridge))).sum(1))/self.ridge)


def downstream(reader,site,layer):return reader in READERS and site in READERS[reader] and site>layer


def expected_cells(layers=LAYERS):return {(L,a,r,s) for L in layers for a in ARMS for r,sites in READERS.items() for s in sites if s>L}


def assert_coverage(rows,layers=LAYERS):
    got={(r['layer'],r['arm'],r['reader'],r['read_layer']) for r in rows if r.get('status')=='OK' and isinstance(r.get('lo'),(int,float)) and np.isfinite(r['lo'])}
    unexpected=got-expected_cells(layers)
    if unexpected:raise ValueError('SMOKE FAILED: unexpected '+repr(sorted(unexpected)))
    missing=expected_cells(layers)-got
    if missing:raise ValueError('SMOKE FAILED: missing '+repr(sorted(missing)))
    return {'cells':len(got),'required_cells':len(expected_cells(layers))}


def output_paths(root,plan,batch):
    """Enumerate every scientific writer path from bank IDs, arms, layers and batch geometry."""
    root=Path(root)
    paths={root/name for name in ('self_patch_precheck.json','matching.json','reuse_receipt.json','layer_decision.json','smoke_pairs.json','target_pairs.json','phase_ledger.jsonl','model_load.jsonl')}
    paths|={root/'natural'/name for name in ('identity.json','encoded.json','checksums.json')}
    paths|={root/'natural'/(r['id']+suffix) for r in plan['records'] for suffix in ('.npz','.partial.npz')}
    for split in ('smoke','pilot','test'):
        base=root/split
        paths|={base/name for name in ('measure_identity.json','model_rows.json','reader_rows.jsonl')}
        n=sum(p['split']==('pilot' if split in ('smoke','pilot') else 'test') for p in plan['pairs'])
        for layer in LAYERS:
            for arm in ARMS:
                for start in range(0,n,batch):
                    paths|={base/f'L{layer}_{arm}_{start:05d}'/name for name in ('rows.json','states.npz','complete.json')}
    return paths|{p.with_name(p.name+'.partial') for p in paths}


_WRITE_RULES=[]

def _write_audit(event,args):
    if not _WRITE_RULES:return
    paths=[];directory=False
    if event=='open':
        path,mode,flags=args
        if isinstance(path,int):return
        if not ((isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))):return
        paths=[path]
    elif event in ('os.rename','os.replace'):paths=list(args[:2])
    elif event in ('os.remove','os.rmdir','os.mkdir'):paths=[args[0]];directory=event in ('os.rmdir','os.mkdir')
    else:return
    allowed,roots=_WRITE_RULES[-1]
    for value in paths:
        if isinstance(value,int):continue
        path=Path(os.fsdecode(value)).resolve()
        if path==Path(os.devnull).resolve():continue
        ok=path in allowed or any(path.is_relative_to(r) for r in roots)
        if directory:ok=ok or any(p.is_relative_to(path) for p in allowed) or any(r.is_relative_to(path) for r in roots)
        if not ok:raise ValueError('X1b-lite WRITE GUARD rejected '+str(path))

sys.addaudithook(_write_audit)

@contextmanager
def write_guard(paths=(),roots=()):
    _WRITE_RULES.append(({Path(p).resolve() for p in paths},{Path(p).resolve() for p in roots}))
    try:yield
    finally:_WRITE_RULES.pop()


def main():
    plan=prepare();save(OUT/'pilot_plan.json',plan)
    print('Metadata plan prepared; no outcome compute')

if __name__=='__main__':main()
