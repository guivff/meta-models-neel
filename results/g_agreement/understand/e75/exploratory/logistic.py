"""EXPLORATORY E75 logistic follow-up, fixed specification; no work on import."""
import json,time,hashlib
from pathlib import Path
import numpy as np
from scipy.special import expit
HERE=Path(__file__).resolve().parent
CATS=['bookkeeping','content','delimiter','format','plan','syntactic']
SEED=20261028

def fit(x,y):
 beta=np.zeros(x.shape[1]);pen=np.ones(len(beta));pen[0]=0
 for _ in range(100):
  p=expit(x@beta);g=x.T@(p-y)+pen*beta
  h=(x.T*(p*(1-p)))@x+np.diag(pen)
  step=np.linalg.solve(h,g);beta-=step
  if np.max(np.abs(step))<1e-10:return beta
 raise RuntimeError('logistic failed to converge')

def design(categories,j,train,aug):
 x=np.column_stack([np.ones(len(j))]+[(categories==c).astype(float)for c in CATS[1:]])
 if aug:
  sd=float(np.std(j[train]));z=(j-float(np.mean(j[train])))/(sd if sd>0 else 1)
  x=np.column_stack([x,z])
 return x

def loo(categories,j,y,aug):
 p=np.zeros(len(y))
 for i in range(len(y)):
  train=np.arange(len(y))!=i;x=design(categories,j,train,aug)
  p[i]=expit(x[i]@fit(x[train],y[train]))
 return p

def loss(y,p):return -(y*np.log(np.clip(p,1e-15,1))+(1-y)*np.log(np.clip(1-p,1e-15,1)))
def ba(y,p):
 if len(np.unique(y))<2:return None
 return float(np.mean([np.mean((p[y==k]>=.5)==k)for k in [0,1]]))

def run():
 source=HERE.parent/'QWEN_BOUND_UNITS.json';plan=json.loads((HERE/'PLAN.json').read_text())
 for f,h in plan['files'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
 assert plan['label']=='EXPLORATORY'
 with (HERE/'ONCE.json').open('x')as f:json.dump({'label':'EXPLORATORY','status':'CLAIMED','seed':SEED},f)
 data=json.loads(source.read_text())['panels']['primary'];results={};started=time.time()
 for reader in ['oracle','nla']:
  rr=sorted([r for r in data if r['reader']==reader],key=lambda r:(r['bank'],r['row']))
  y=np.array([r['truth']=='REPORTED'for r in rr],dtype=float);j=np.array([r['j_fraction']for r in rr]);cat=np.array([r['category']for r in rr])
  base=loo(cat,j,y,False);aug=loo(cat,j,y,True);lb=loss(y,base);la=loss(y,aug)
  observed=np.array([np.mean(lb-la),ba(y,aug)-ba(y,base)])
  rng=np.random.default_rng(SEED);bs=[];invalid=0
  for _ in range(10000):
   ix=rng.integers(0,len(y),len(y));b=ba(y[ix],base[ix]);a=ba(y[ix],aug[ix]);invalid+=int(a is None)
   bs.append([float(np.mean((lb-la)[ix])),a-b if a is not None else np.nan])
  bs=np.array(bs);ci=np.nanquantile(bs,[.025,.975],axis=0).T.tolist()
  rng=np.random.default_rng(SEED);null=[]
  for k in range(1000):
   jp=j.copy()
   for c in CATS:
    ix=np.where(cat==c)[0];jp[ix]=rng.permutation(j[ix])
   pp=loo(cat,jp,y,True);null.append([float(np.mean(lb-loss(y,pp))),ba(y,pp)-ba(y,base)])
   if (k+1)%200==0:print('EXPLORATORY',reader,k+1,'permutations',flush=True)
  null=np.array(null)
  results[reader]={'label':'EXPLORATORY','n':len(y),'reported':int(y.sum()),'category_only':{'loo_log_loss':float(np.mean(lb)),'loo_balanced_accuracy':ba(y,base)},'category_plus_J':{'loo_log_loss':float(np.mean(la)),'loo_balanced_accuracy':ba(y,aug)},'improvement':dict(zip(['log_loss_reduction','balanced_accuracy_increase'],observed.tolist())),'bootstrap95':dict(zip(['log_loss_reduction','balanced_accuracy_increase'],ci)),'bootstrap':{'draws':10000,'seed':SEED,'single_class_BA_draws':invalid,'conditional_on_fixed_OOF_predictions':True},'permutation':{'count':1000,'seed':SEED,'p_plus_one':dict(zip(['log_loss_reduction','balanced_accuracy_increase'],((1+(null>=observed).sum(axis=0))/1001).tolist())),'percentile95':dict(zip(['log_loss_reduction','balanced_accuracy_increase'],np.quantile(null,.95,axis=0).tolist())),'null':null.tolist()},'rows':[dict(bank=r['bank'],row=r['row'],truth=r['truth'],category=r['category'],J_fraction=r['j_fraction'],category_only_probability=float(b),category_plus_J_probability=float(a))for r,b,a in zip(rr,base,aug)]}
  print('EXPLORATORY',reader,'done',flush=True)
 out={'label':'EXPLORATORY','authority':'1e879d02 and direct user request','R_P1':'UNCHANGED NOT EVALUABLE','results':results,'wall_seconds':time.time()-started}
 (HERE/'RESULTS.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':run()
