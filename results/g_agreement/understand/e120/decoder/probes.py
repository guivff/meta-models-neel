"""E120b pre-output CPU kernel: E113 recipe on E85 dev count; no data at import."""
import warnings
from collections import Counter
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
CS=(.01,.1,1.,10.,100.);SEED=20261029
POSITIONS=('injected_activation','first_generated_token')
def fit_dev(x,y):
 x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=int)
 assert x.ndim==2 and len(x)==len(y) and np.isfinite(x).all() and set(y)=={0,1} and min(np.bincount(y))>=5
 scores=[];folds=list(StratifiedKFold(5,shuffle=True,random_state=SEED).split(x,y))
 def model(c):return make_pipeline(StandardScaler(),LogisticRegression(C=c,max_iter=2000,solver='lbfgs',random_state=SEED))
 with warnings.catch_warnings():
  warnings.simplefilter('error',ConvergenceWarning)
  for c in CS:
   auc=[]
   for train,valid in folds:
    m=model(c).fit(x[train],y[train]);auc.append(float(roc_auc_score(y[valid],m.decision_function(x[valid]))))
   scores.append(dict(C=c,fold_AUROC=auc,mean_AUROC=float(np.mean(auc))))
  best=max(range(len(CS)),key=lambda i:scores[i]['mean_AUROC']);m=model(CS[best]).fit(x,y)
 return m,dict(selected_C=CS[best],dev_CV=scores,seed=SEED,test_used_for_selection=False)

def reading(grid):
 assert set(grid)=={str(l) for l in range(64)}
 for v in grid.values():assert set(v)==set(POSITIONS) and all(np.isfinite(x) and 0<=x<=1 for x in v.values())
 late=[grid[str(l)]['first_generated_token'] for l in range(48,64)]
 return dict(R_EV2='DECODER_STATE_CARRIED' if max(late)>=.90 else 'STATE_NOT_SURVIVING' if max(late)<=.65 else 'INCONCLUSIVE',first_generated_late_max=max(late),first_generated_late_min=min(late),descriptive=True)

def validate_metadata(order,index,labels):
 assert set(order)=={'dev','test'} and len(index)==len(labels)==600
 by={x['public_id']:x for x in labels};assert len(by)==600
 ix={x['id']:x for x in index};assert len(ix)==600
 groups={};ys={};seen=[];sets={};tokens={}
 for split,n,percell in [('dev',200,50),('test',400,100)]:
  rows=order[split];assert len(rows)==n;cnt=Counter();yy=[];ss=set();celltokens={}
  for r in rows:
   i=r['id'];assert i in by and r==ix[i];a=by[i];assert a['split']==r['split']==split and a['genre'] in [0,1] and a['addressed'] in [0,1]
   assert type(r['first_token_id']) is int and r['first_token_id']>=0
   assert r['source_layer']==44 and r['injected_position']>=0 and r['first_generated_position']>r['injected_position']
   key=f"genre={a['genre']},addressed={a['addressed']}";cnt[key]+=1;celltokens.setdefault(key,Counter())[r['first_token_id']]+=1;yy.append(a['addressed']);ss.add(a['matched_set']);seen.append(i)
   groups.setdefault(a['matched_set'],[]).append(a)
  assert len(cnt)==4 and set(cnt.values())=={percell};ys[split]=np.asarray(yy);sets[split]=ss
  tokens[split]={k:dict(n=sum(c.values()),constant=len(c)==1,token_id_counts=dict(sorted(c.items()))) for k,c in sorted(celltokens.items())}
 assert len(set(seen))==600 and set(seen)==set(by) and sets['dev'].isdisjoint(sets['test'])
 for g in groups.values():assert len(g)==4 and {(r['genre'],r['addressed']) for r in g}=={(0,0),(0,1),(1,0),(1,1)} and len({r['split'] for r in g})==1
 combined={}
 for key in tokens['dev']:
  c=Counter(tokens['dev'][key]['token_id_counts']);c.update(tokens['test'][key]['token_id_counts']);combined[key]=dict(n=sum(c.values()),constant=len(c)==1,token_id_counts=dict(sorted(c.items())))
 tokens['combined']=combined
 return ys,tokens
