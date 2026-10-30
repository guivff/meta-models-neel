"""E115b: freeze dev deciles before reading original E94 test classes, once."""
from pathlib import Path
import json,hashlib,subprocess,time
from datetime import datetime,timezone
import numpy as np
from metrics import j_fraction
from metrics_b import gate_counts
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def rates(c):
 n=c[...,0];reports=c[...,1];correct=c[...,2]
 return np.divide(correct,reports,out=np.full(reports.shape,np.nan,dtype=float),where=reports>0),reports/n

def interval(x):
 x=np.asarray(x);x=x[np.isfinite(x)];return np.quantile(x,[.025,.975]).tolist() if len(x) else None

def main():
 start=time.monotonic();plan=read(HERE/'PART_B_PLAN.json');assert sha(plan['binding'])==plan['binding_sha256'];d=read(plan['binding'])
 for f,h in {**d['pins'],**plan['code_pins']}.items():assert sha(f)==h,f
 for f in plan['code_pins']:assert subprocess.check_output(['git','show','HEAD:'+str(Path(f).relative_to(ROOT))],cwd=ROOT)==Path(f).read_bytes()
 cache=ROOT/'cache/g_agreement/understand/e115';guard=cache/'PART_B_ONCE.json';out=HERE/'part_b_once';assert not out.exists()
 with guard.open('x') as f:json.dump(dict(created_utc=datetime.now(timezone.utc).isoformat(),plan_sha256=sha(HERE/'PART_B_PLAN.json')),f)
 q=np.load(d['basis'],allow_pickle=False).astype(float);mu=np.load(d['mean_source'],allow_pickle=False).astype(float).mean(0);arr={};thresholds={};quantiles=np.arange(1,10)/10
 def vectors(refs):
  xs=[]
  for r in refs:
   if r['file'] not in arr:arr[r['file']]=np.load(r['file'],allow_pickle=False)
   xs.append(arr[r['file']][r['index']])
  return np.stack(xs)
 for key,g in d['groups'].items():thresholds[key]=np.quantile(j_fraction(vectors(g['dev']),mu,q),quantiles).tolist()
 tp=cache/'PART_B_DEV_THRESHOLDS.json';write(tp,dict(status='FROZEN_BEFORE_E94_CLASSES_OPEN',quantiles=quantiles.tolist(),thresholds=thresholds,plan_sha256=sha(HERE/'PART_B_PLAN.json')))
 # Existing sealed classes are loaded only after all dev thresholds have been persisted.
 rows=read(d['outcomes']);paired={}
 for r in rows:
  if r['bank'].startswith('E67'):continue
  k=(r['bank'],r['unit']);g=paired.setdefault(k,{});assert r['reader'] not in g;g[r['reader']]=r
 pairs={k:v for k,v in paired.items() if set(v)=={'oracle','nla'} and all(v[r]['class'] is not None for r in v)}
 assert len(pairs)==4313
 rng=np.random.default_rng(20261029);total=np.zeros((10,3),dtype=np.int64);boot_total=np.zeros((2000,10,3),dtype=np.int64);perrow={};used=set();private={}
 for key,g in d['groups'].items():
  fs=j_fraction(vectors(g['test']),mu,q);included=[i for i,r in enumerate(g['test']) if (g['bank'],r['id']) in pairs]
  if not included:continue
  correct=[];agree=[];clusters=[]
  for i in included:
   ident=g['test'][i]['id'];p=pairs[(g['bank'],ident)];o=p['oracle'];n=p['nla'];assert o['stratum']==g['row'] and n['stratum']==g['row'];used.add((g['bank'],ident));correct.append(o['class']=='correct');agree.append(o['class']==n['class'] and o['class']!='no mention');clusters.append(o['cluster'])
  counts=gate_counts(correct,agree,fs[included],thresholds[key]);unique=sorted(set(clusters));ct=np.stack([counts[[i for i,c in enumerate(clusters) if c==u]].sum(0) for u in unique]);draw=ct[rng.integers(0,len(ct),size=(2000,len(ct)))].sum(1);point=ct.sum(0);prec,cov=rates(point);bp,bc=rates(draw)
  curves=[]
  for j in range(10):curves.append(dict(quantile=None if j==0 else float(quantiles[j-1]),tau=None if j==0 else thresholds[key][j-1],n=int(point[j,0]),reports=int(point[j,1]),correct_reports=int(point[j,2]),precision=float(prec[j]) if np.isfinite(prec[j]) else None,coverage=float(cov[j]),precision_ci=interval(bp[:,j]),coverage_ci=interval(bc[:,j])))
  perrow[key]=dict(n=len(included),dev_n=len(g['dev']),curve=curves);total+=point;boot_total+=draw;private[key]=dict(test_ids=[g['test'][i]['id'] for i in included],fractions=fs[included].tolist())
 prec,cov=rates(total);bp,bc=rates(boot_total);curves=[]
 for j in range(10):curves.append(dict(quantile=None if j==0 else float(quantiles[j-1]),n=int(total[j,0]),reports=int(total[j,1]),correct_reports=int(total[j,2]),precision=float(prec[j]) if np.isfinite(prec[j]) else None,coverage=float(cov[j]),precision_ci=interval(bp[:,j]),coverage_ci=interval(bc[:,j])))
 fullreports=[p for p in pairs.values() if p['oracle']['class']==p['nla']['class'] and p['oracle']['class']!='no mention'];assert len(fullreports)==1001 and sum(p['oracle']['class']=='correct' for p in fullreports)==943
 missing={}
 for bank,ident in sorted(set(pairs)-used):
  k='E56_injection' if bank=='E56' and ident.startswith('injection') else bank;missing[k]=missing.get(k,0)+1
 result=dict(experiment='E115b',status='COMPLETE_ONCE_WITH_EXPLICIT_UNAVAILABLE_ROWS',full_e94_baseline=dict(n=4313,reports=1001,correct=943,precision=943/1001,coverage=1001/4313),evaluable_subset=dict(n=len(used),rows=len(perrow),curve=curves),within_row=perrow,not_evaluable_counts=missing,unavailable=d['unavailable'],full_e94_gain_reading='NOT EVALUABLE: dev-decile input unavailable for some original paired rows; no missing-to-zero or test-threshold substitution',subset_point_reading='GAIN_AT_REGISTERED_POINT_CRITERION' if any((np.isfinite(prec[j]) and ((prec[j]> .942 and cov[j]>=.23) or (prec[j]>=prec[0] and cov[j]>cov[0]))) for j in range(1,10)) else 'NO_GAIN_AT_REGISTERED_POINT_CRITERION',dev_thresholds_sha256=sha(tp),bootstrap=dict(draws=2000,seed=20261029,unit='original source-item clusters within row; rows fixed',ci='percentile; precision undefined when no reports'),recipe='same E80c J384 and original518 mean as a; tau row-specific dev decile cutpoints .1.. .9, strictly greater',wall_seconds=time.monotonic()-start,gpu_hours=0)
 out.mkdir();write(out/'RESULTS.json',result);pf=cache/'PART_B_FRACTIONS.PRIVATE.json';write(pf,private);pf.chmod(0o600);write(out/'ANALYSIS_SEAL.json',dict(status=result['status'],plan_sha256=sha(HERE/'PART_B_PLAN.json'),private_fractions_sha256=sha(pf),dev_thresholds_sha256=sha(tp),files={'RESULTS.json':sha(out/'RESULTS.json')}));print(json.dumps({k:v for k,v in result.items() if k!='within_row'}))
if __name__=='__main__':main()
