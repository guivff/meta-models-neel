"""§79 sealed-score joins; vendored probes/metrics; fixed H1/H2 and top10 selection."""
from __future__ import annotations
import argparse,json
from dataclasses import asdict
from pathlib import Path
import numpy as np
from . import protocol as P,corpus as C,features as F


class CVUnavailable(ValueError):pass

def cv_probe(h,y,groups):
 import common
 import torch
 from mats import probes,metrics
 groups=np.asarray(groups);y=np.asarray(y);pred=np.empty(len(y),dtype=float)
 if len(set(groups))<5:raise CVUnavailable('too few document groups for5folds')
 folds=probes.group_folds(groups,k=5,seed=C.SEED)
 for test in folds:
  train=np.setdiff1d(np.arange(len(y)),test)
  if len(np.unique(y[train]))<2:raise CVUnavailable('single-class CV training fold')
 summary=probes.cv_auroc(h,y,groups,k=5,lam=1e-3,seed=C.SEED)
 for test in folds:
  train=np.setdiff1d(np.arange(len(y)),test);model=probes.fit_logreg(h[train],torch.as_tensor(y[train]),lam=1e-3);pred[test]=model.decision(h[test]).cpu().numpy()
 if not np.isclose(metrics.auroc_labels(pred,y),summary['auroc'],atol=1e-6):raise ValueError('vendored CV/OOF mismatch')
 return pred


def primary_rules(rows,draws=2000,seed=C.SEED):
 by={(r['feature'],r['reader']):r for r in rows};rng=np.random.default_rng(seed);a=[];b=[];paired=[]
 for r in rows:
  if r['reader']=='olens' and r['evaluable']:
   (a if r['class_label'] in ('count-like','state-like') else b).append(r['gap'])
  if r['reader']=='olens' and r['class_label'] in ('count-like','state-like'):
   other=by.get((r['feature'],'nla'))
   if r['evaluable'] and other and other['evaluable']:paired.append(r['gap']-other['gap'])
 def result(name,point,boots,n):
  if point is None:return {'claim':name,'status':'NOT EVALUABLE','point':None,'ci95':None,'n':n}
  lo,hi=np.percentile(boots,[2.5,97.5]).tolist();return {'claim':name,'status':'CONFIRMED' if point>=.10 and lo>0 else 'NOT MET','point':float(point),'ci95':[lo,hi],'n':n}
 if a and b:
  a,b=np.asarray(a),np.asarray(b);boot=[rng.choice(a,len(a),replace=True).mean()-rng.choice(b,len(b),replace=True).mean() for _ in range(draws)];h1=result('H1',a.mean()-b.mean(),boot,{'count_state':len(a),'semantic':len(b)})
 else:h1=result('H1',None,None,{'count_state':len(a),'semantic':len(b)})
 if paired:
  paired=np.asarray(paired);boot=[rng.choice(paired,len(paired),replace=True).mean() for _ in range(draws)];h2=result('H2',paired.mean(),boot,len(paired))
 else:h2=result('H2',None,None,0)
 return [h1,h2]


def top_candidates(rows,n=10):
 pool=[r for r in rows if r['reader']=='olens' and r['evaluable'] and not r['w1_overlap']]
 return sorted(pool,key=lambda r:(-r['gap'],r['feature']))[:n]


def clean(value):
 if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
 if isinstance(value,list):return [clean(v) for v in value]
 if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
 if isinstance(value,np.integer):return int(value)
 return value


def analyse(bank,native,labels_path,out,kind="real"):
 if kind not in ("real","test"):raise ValueError("invalid analysis kind")
 import common
 import torch
 from mats import metrics
 P.verify_freeze();seal=P.verify(native,'prediction_seal.s79.json');docs,positions,assign,registry=P.inputs(bank)
 if seal['input_seal_sha256']!=C.sha(Path(bank)/'INPUT_SEAL.json') or seal['freeze_sha256']!=C.sha(C.OUT/'FREEZE.json'):raise ValueError('native seal input/freeze mismatch')
 raw=C.rows(Path(native)/'scores.s79.jsonl');P.score_coverage(raw,assign,kind)
 if {(r['run_id'],r['code_sha256']) for r in raw}!={(seal['run_id'],seal['code_sha256'])}:raise ValueError('prediction seal/row identity mismatch')
 if kind=='real':
  if 'warmup.s79.json' not in seal['files']:raise ValueError('unsealed warmup proof')
  wp=json.loads((Path(native)/'warmup.s79.json').read_text());stage=json.loads((Path(native)/'stage_complete.s79.json').read_text());P.validate_warmup(wp,stage['at'])
  if (wp['run_id'],wp['code_sha256'])!=(seal['run_id'],seal['code_sha256']):raise ValueError('warmup/score identity mismatch')
  from . import kernel_preflight as K
  kp=json.loads((Path(native)/'kernel_preflight.s79.json').read_text());K.validate_metadata(kp)
  if set(kp['dispatch'])!=set(K.SYMBOLS) or not all(v['transformers_original_package_dispatch'] for v in kp['dispatch'].values()):raise ValueError('native fast-kernel proof missing')
 # All source/score coverage and hashes are verified before opening labels.
 input_seal=json.loads((Path(bank)/'INPUT_SEAL.json').read_text());expected=input_seal['private_label_files']['labels.selected.DO_NOT_STAGE.jsonl']
 if C.sha(labels_path)!=expected:raise ValueError('wrong frozen labels')
 labels=C.rows(labels_path);lm={(r['feature'],r['id']):r for r in labels};am={(r['feature'],r['id']):r for r in assign}
 if set(lm)!=set(am) or len(lm)!=len(labels):raise ValueError('label key coverage')
 pfile=json.loads((Path(native)/'positions.s79.json').read_text())
 if pfile!=positions:raise ValueError('state row order/source positions changed')
 state_index={r['id']:i for i,r in enumerate(positions)};arrays={site:np.load(Path(native)/f'acts{site}.s79.npy',mmap_mode='r',allow_pickle=False) for site in [42,44]}
 for site,h in arrays.items():
  if h.ndim!=2 or len(h)!=len(positions) or not np.isfinite(h).all():raise ValueError('state array shape/nonfinite')
 sm={(r['feature'],r['id'],r['reader'],r['arm']):r['score'] for r in raw};rows=[];oof=[]
 for feature in sorted({r['feature'] for r in assign}):
  ids=sorted(r['id'] for r in assign if r['feature']==feature);meta=[lm[feature,i] for i in ids];y=np.array([r['value'] for r in meta]);groups=np.array([r['source_group_id'] for r in meta]);spec=F.BY_ID[feature]
  for reader,site in P.SITES.items():
   true=np.array([sm[feature,i,reader,'true'] for i in ids]);mis=np.array([sm[feature,i,reader,'mismatched'] for i in ids]);native_true=asdict(metrics.auroc_ci(true,y,groups,n_boot=2000,seed=C.SEED));native_mis=asdict(metrics.auroc_ci(mis,y,groups,n_boot=2000,seed=C.SEED))
   rec={**P.stamp(kind),'feature':feature,'reader':reader,'site':site,'class_label':spec.kind,'definition':spec.definition,'w1_overlap':list(spec.w1_overlap),'n':len(y),'n_groups':len(set(groups)),'native_true':native_true,'native_mismatched':native_mis,'probe':None,'gap':None,'gap_ci95':None,'evaluable':False,'checkpoint':'agu18dec/olens_and_ar@c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600' if reader=='olens' else 'ceselder/qwen3.6-27b-nla-rl@5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f/av_rl_adapters/iter_000400'}
   try:
    h=torch.from_numpy(np.array(arrays[site][[state_index[i] for i in ids]],copy=True));pred=cv_probe(h,y,groups);pr=asdict(metrics.auroc_ci(pred,y,groups,n_boot=2000,seed=C.SEED));rec['probe']=pr
    lo,hi=metrics.cluster_bootstrap(lambda k:metrics.auroc_labels(pred[k],y[k])-metrics.auroc_labels(true[k],y[k]),groups,n_boot=2000,seed=C.SEED);rec.update(gap=float(pr['auroc']-native_true['auroc']),gap_ci95=[lo,hi]);rec['evaluable']=pr['auroc']>=.85 and native_mis['auroc']<=.60
    rec['status']='EVALUABLE' if rec['evaluable'] else 'NOT DECODABLE' if pr['auroc']<.85 else 'NOT EVALUABLE_MISMATCH_GATE'
    oof.extend({**P.stamp(kind),'feature':feature,'id':i,'site':site,'score':float(v)} for i,v in zip(ids,pred))
   except CVUnavailable as e:rec['status']='NOT EVALUABLE_PROBE_CV';rec['error']=str(e)
   rows.append(rec)
 results=clean({'section':79,'status':'COMPLETE','claims':primary_rules(rows),'rows':rows,'pre_capture_drops':json.loads((C.OUT/'ELIGIBILITY.json').read_text()),'native_prediction_seal_sha256':C.sha(Path(native)/'prediction_seal.s79.json'),'fixed_oof_bootstrap':'source-document clustered; probe OOF predictions fixed, not refit within bootstrap'});out=Path(out);out.mkdir(parents=True,exist_ok=False);C.save(out/'RESULTS.json',results);C.jsonl(out/'probe_oof.jsonl',oof)
 top=clean(top_candidates(rows));C.save(out/'TOP10.json',{'section':79,'status':'FROZEN_BEFORE_ANY_S84_ITEMS','selection':'descending Oracle gap; eligible native44 probe≥.85 / mismatch≤.60; exclude frozen W1 overlap; ties featureID','candidates':top,'results_sha256':C.sha(out/'RESULTS.json'),'freeze_sha256':C.sha(C.OUT/'FREEZE.json')})
 lines=['# §79 probe-gap screen','',f"Complete frozen cohort; {len(rows)//2} retained features,43pre-capture drops. No post-hoc sign flipping or feature changes.",'','| Claim | Point contrast | 95% CI | Verdict |','|---|---:|---|---|']
 for r in results['claims']:lines.append(f"| {r['claim']} | {r['point']} | {r['ci95']} | {r['status']} |")
 lines+=['','| Feature | Class | Reader/site | Probe AUROC [95%] | Asked AUROC [95%] | Mismatch AUROC [95%] | Gap [95%] | Status |','|---|---|---|---|---|---|---|---|']
 def fmt(x):return 'NOT EVALUABLE' if not x else f"{x['auroc']:.3f} [{x['lo']:.3f},{x['hi']:.3f}]"
 for r in rows:lines.append(f"| {r['feature']} | {r['class_label']} | {r['reader']}/{r['site']} | {fmt(r['probe'])} | {fmt(r['native_true'])} | {fmt(r['native_mismatched'])} | {r['gap']} {r['gap_ci95']} | {r['status']} |")
 lines+=['','## Frozen candidates for §84','',*['- '+r['feature']+f" (Oracle gap {r['gap']:.3f})" for r in top],'','A matched opposite-value donor permutation is not independent validation: its teacher-forced score is a cached native request alias, and its AUROC is1−TRUE AUROC. Semantic controls are frozen lexical operational indicators. LaTeX corpus rows are solution fragments; source-document groups, not independent token rows, define CV and AUROC bootstraps.']
 (out/'RESULTS.md').write_text('\n'.join(lines)+'\n');P.seal(out,['RESULTS.json','TOP10.json','RESULTS.md','probe_oof.jsonl'],'ANALYSIS_SEAL.json',**P.stamp(kind))

def main():
 p=argparse.ArgumentParser()
 for k in ['bank','native','labels','out']:p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args();analyse(a.bank,a.native,a.labels,a.out)
if __name__=='__main__':main()
