"""X1 design/CPU preparation. No model imports, downloads or outcome selection."""
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
OUT = ROOT/'results/g_agreement/r/remainder/x1'
DATA_REL = Path('cache/g_agreement/r/remainder/x1')
CACHE = ROOT/DATA_REL
BANK = ROOT/'projects/g_agreement/dataset/items_re.json'
SEED = 20261020
LAYERS = (24, 28)
ARMS = ('bridge_patch', 'class_mean', 'answer_patch', 'random_bridge', 'natural', 'random_answer')
READERS = {'olens': (44,), 'nla': (42,), 'jlens': (28, 42), 'skip_a': (42,)}
CALIPER = .05
CM_MIN = 4
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
    files=sorted(Path(__file__).parent.glob('remainder_x1*.py'))
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
    bank=records(path);pool=[r for r in bank if r['split']=='pool' and pair_candidates(r,bank)]
    # Round-robin template strata, seeded order, chosen without activations/outcomes.
    strata={t:sorted([r for r in pool if r['template']==t],key=lambda r:rank('pilot',r['id'])) for t in sorted({r['template'] for r in pool})}
    order=[]
    while any(strata.values()):
        for t in sorted(strata):
            if strata[t]:order.append(strata[t].pop(0))
    if len(order)<40:raise ValueError('Need 20 pilot and 20 specificity pool items')
    pilot=order[:PILOT_N];cal=order[PILOT_N:2*PILOT_N];pilot_ids={r['id'] for r in pilot};cal_ids={r['id'] for r in cal}
    cm=[r for r in bank if r['split']=='pool' and r['id'] not in pilot_ids]
    ncm=Counter(r['bridge'] for r in cm)
    plans=[]
    for r in pilot+[r for r in bank if r['split']=='test']:
        candidates=pair_candidates(r,bank)
        supported=[k for k in candidates if ncm[next(x['bridge'] for x in bank if x['id']==k)]>=CM_MIN and ncm[r['bridge']]>=CM_MIN]
        plans.append({'recipient':r['id'],'split':'pilot' if r['id'] in pilot_ids else 'test',
                      'class_mean_supported_donors':supported,'donor_candidates':candidates,'nominal_donor':candidates[0] if candidates else None,
                      'status':'PENDING_ACTIVATION_NORMS' if candidates else 'NO_SAME_RELATION_DONOR'})
    return {'experiment':'X1','seed':SEED,'bank':str(Path(path).relative_to(ROOT)) if Path(path).is_relative_to(ROOT) else str(path),
            'bank_sha256':sha(path),'records':bank,'pairs':plans,'pilot_ids':sorted(pilot_ids),'specificity_ids':sorted(cal_ids),
            'cm_fit_ids':[r['id'] for r in cm],'detector_fit_ids':[r['id'] for r in cm if r['id'] not in cal_ids],
            'layers':list(LAYERS),'primary_layer':None,'caliper':CALIPER,'norm_matching':'exact natural donor replacements; 5% distance caliper; class mean exact norm',
            'outcomes_computed':False,'metadata_only':True,'status':'DRAFT_NUMBER_AND_BOOKING_PENDING'}


def norm_matching(rec,donor,random_ids,states,layer):
    """Immutable donor vectors; no scaling. Each natural arm within 5% of arm a's delta norm."""
    def vec(i,pos):return np.asarray(states[i][layer][pos],dtype=np.float64)
    target=np.linalg.norm(vec(donor,'bridge')-vec(rec,'bridge'))
    if not np.isfinite(target) or target<=0:return None
    answer=np.linalg.norm(vec(donor,'answer')-vec(rec,'answer'))
    if abs(answer/target-1)>CALIPER:return None
    matches={}
    for site in ('bridge','answer'):
        eligible=[]
        for k in random_ids:
            norm=np.linalg.norm(vec(k,site)-vec(rec,site));error=abs(norm/target-1)
            if np.isfinite(error) and error<=CALIPER:eligible.append((rank(rec,donor,site,k),k,float(norm)))
        if not eligible:return None
        _,key,norm=min(eligible);matches['random_'+site]={'donor':key,'norm':norm}
    return {'norm':float(target),'answer_norm':float(answer),**matches}


def freeze_pairs(plan,states,layer,split):
    bank={r['id']:r for r in plan['records']};out=[];excluded=[]
    for p in plan['pairs']:
        if p['split']!=split:continue
        rec=bank[p['recipient']];picked=None
        for did in p['donor_candidates']:
            donor=bank[did];match=norm_matching(rec['id'],did,unrelated(rec,donor,plan['records']),states,layer)
            if match:
                picked={**p,'donor':did,'layer':layer,**match,'status':'MATCHED'};break
        (out if picked else excluded).append(picked or {**p,'reason':'no complete natural-arm 5% norm match'})
    return out,excluded


def class_means(plan,states,layer):
    bank={r['id']:r for r in plan['records']};by={}
    for iid in plan['cm_fit_ids']:by.setdefault(bank[iid]['bridge'],[]).append(states[iid][layer]['bridge'])
    return {b:np.asarray(v,dtype=np.float32).mean(0) for b,v in by.items() if len(v)>=CM_MIN}


def added_direction(pair,bank,means):
    v=means[bank[pair['donor']]['bridge']]-means[bank[pair['recipient']]['bridge']]
    n=float(np.linalg.norm(v))
    if not np.isfinite(n) or n==0:raise ValueError('Undefined class-mean added direction')
    return v*(pair['norm']/n)


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


def expected_cells():return {(L,a,r,s) for L in LAYERS for a in ARMS for r,sites in READERS.items() for s in sites if s>L}


def assert_coverage(rows):
    got={(r['layer'],r['arm'],r['reader'],r['read_layer']) for r in rows if r.get('status')=='OK' and isinstance(r.get('lo'),(int,float)) and np.isfinite(r['lo'])}
    unexpected=got-expected_cells()
    if unexpected:raise ValueError('SMOKE FAILED: unexpected '+repr(sorted(unexpected)))
    missing=expected_cells()-got
    if missing:raise ValueError('SMOKE FAILED: missing '+repr(sorted(missing)))
    return {'cells':len(got),'required_cells':len(expected_cells())}


def output_paths(root,plan,batch):
    """Enumerate every scientific writer path from bank IDs, arms, layers and batch geometry."""
    root=Path(root)
    paths={root/name for name in ('self_patch_precheck.json','pilot_caliper_audit.json','pilot_shortfall.json','layer_decision.json','smoke_pairs.json','target_pairs.json','phase_ledger.jsonl','model_load.jsonl')}
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
        if not ok:raise ValueError('X1 WRITE GUARD rejected '+str(path))

sys.addaudithook(_write_audit)

@contextmanager
def write_guard(paths=(),roots=()):
    _WRITE_RULES.append(({Path(p).resolve() for p in paths},{Path(p).resolve() for p in roots}))
    try:yield
    finally:_WRITE_RULES.pop()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['prepare'],required=True);a=p.parse_args()
    plan=prepare();save(OUT/'pilot_plan.json',{**plan,**provenance()})
    summary={'pilot_recipients':len(plan['pilot_ids']),'test_recipients':sum(p['split']=='test' for p in plan['pairs']),
             'with_candidate_donor':dict(Counter(p['split'] for p in plan['pairs'] if p['donor_candidates'])),
             'no_candidate_with_cm_support':dict(Counter(p['split'] for p in plan['pairs'] if not p['class_mean_supported_donors'])),
             'detector_fit':len(plan['detector_fit_ids']),'cm_fit':len(plan['cm_fit_ids']),
             'state_norms_and_layer_selection':'PENDING_GPU; no model or gate outcomes computed'}
    save(OUT/'cpu_plan_summary.json',{**summary,**provenance()});print(json.dumps(summary))

if __name__=='__main__':main()
