"""CPU-only complete-set SA analysis. No model or judge calls."""
import json, hashlib
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from sklearn.metrics import roc_auc_score
from . import sa_contract as S

SEED=20261020

def bh(p):
 p=np.asarray(p,float);order=np.argsort(p);q=np.empty(len(p));q[order]=np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1];return np.minimum(q,1)

def boot_weights(corpora,families,n=10000):
 rng=np.random.default_rng(SEED);C=len(corpora);P=len(families);groups=[np.flatnonzero(np.array(corpora)==x) for x in sorted(set(corpora))];fg=[np.flatnonzero(np.array(families)==x) for x in sorted(set(families))]
 out=[]
 for scheme in range(3):
  w=np.zeros((n,C*P),np.float64)
  for b in range(n):
   if scheme==0:
    for c in range(C):
     ids=c*P+rng.integers(P,size=P);np.add.at(w[b],ids,1/(C*P))
   else:
    cs=np.concatenate([rng.choice(groups[g],size=len(groups[g]),replace=True) for g in rng.integers(len(groups),size=len(groups))])
    ps=rng.integers(P,size=P) if scheme==1 else np.concatenate([rng.choice(fg[g],size=len(fg[g]),replace=True) for g in rng.integers(len(fg),size=len(fg))])
    np.add.at(w[b],(cs[:,None]*P+ps).ravel(),1/(len(cs)*len(ps)))
  out.append(w)
 return out

def interval(x,weights,threshold=0):
 x=np.asarray(x,float).ravel();estimate=float(x.mean());draws=[w@x for w in weights]
 c95=[np.quantile(b,[.025,.975]).tolist() for b in draws];c975=[np.quantile(b,[.0125,.9875]).tolist() for b in draws]
 # Exploratory null-centered bootstrap tail at the requested contrast threshold.
 pv=max((1+np.count_nonzero(b-estimate>=estimate-threshold))/(len(b)+1) for b in draws)
 return {'estimate':estimate,'ci95_by_scheme':c95,'ci95':[min(x[0] for x in c95),max(x[1] for x in c95)],'ci975':[min(x[0] for x in c975),max(x[1] for x in c975)],'exploratory_p':pv}

def main():
 root=S.ROOT/'cache/g_agreement/r/neel5/sa/complete_20261021';out=S.ROOT/'results/g_agreement/r/neel5/sa/analysis_20261021'
 assert json.loads((root/'status.json').read_text())['logical_rows']==16800
 manifest=json.loads((out/'PANEL_INPUT_MANIFEST.json').read_text())
 # Reverify the pinned complete set before using values.
 for f in manifest['cells']:
  assert hashlib.sha256(Path(f['path']).read_bytes()).hexdigest()==f['sha256']
 d=json.loads(S.DESIGN.read_text());ids=[c['concept_id'] for c in d['concepts']];ev=d['evaluation_concepts'];prompts=[p for p in d['prompts'] if p['split']=='evaluation'];pids=[p['prompt_id'] for p in prompts];arms=d['conditions'];layers=['42','44']
 sums={l:{c:None for c in ids} for l in layers};counts={c:0 for c in ids};states={};obs={};beh={};open_rows={}
 joined_at=datetime.now(timezone.utc).isoformat()
 for f in sorted((root/'cells').glob('*.json')):
  row=json.loads(f.read_text());k=row['key'];v=row['value']
  if k[0]=='state':
   _,split,c,p,a=k
   if split=='train':
    counts[c]+=1
    for l in layers:
     x=np.asarray(v['states'][l],float);sums[l][c]=x if sums[l][c] is None else sums[l][c]+x
   elif split=='evaluation':
    states[c,p,a]={l:np.asarray(v['states'][l],float) for l in layers};beh[c,p,a]=v['behaviour']
    z=beh[c,p,a];computed=bool(z['kl']<=d['pool_kl_max_nats'] and z['natural']['eos'] and z['edited']['eos'] and z['natural']['tokens']==z['edited']['tokens']);assert computed==bool(z['invisible'])
  elif k[0]=='observation':
   obs[tuple(k[1:])]=v
 assert len(obs)==16800 and len(states)==1200 and all(n==50 for n in counts.values())
 corpora=[next(c['source_corpus'] for c in d['concepts'] if c['concept_id']==x) for x in ev]
 weights=boot_weights(corpora,[p['template_family'] for p in prompts]);shape=(len(ev),len(pids));hits={};valid={};auroc={}
 for method in ['oracle','nla','prompt_only','jlens','labelled_probe']:
  for a in arms:
   values=[obs[c,p,a,method,'closed'] for c in ev for p in pids]
   valid[method,a]=sum(bool(v['valid']) for v in values)
   if valid[method,a]==400:hits[method,a]=np.array([c in obs[c,p,a,method,'closed']['top5'] for c in ev for p in pids],float).reshape(shape)
 for l in layers:
  bank=np.stack([sums[l][c]/counts[c] for c in ids]);norm=np.linalg.norm(bank,axis=1);assert np.isfinite(bank).all() and (norm>0).all();bank/=norm[:,None]
  for a in arms:
   xx=np.stack([states[c,p,a][l] for c in ev for p in pids]);nn=np.linalg.norm(xx,axis=1);assert (nn>0).all();scores=(xx/nn[:,None])@bank.T
   hits['cosine_L'+l,a]=np.array([c in S.top5(s,ids) for (c,p),s in zip([(c,p) for c in ev for p in pids],scores)],float).reshape(shape)
   hits['linear_L'+l,a]=np.array([c in obs[c,p,a,'labelled_probe','closed']['site_results'][l]['top5'] for c in ev for p in pids],float).reshape(shape)
 # Exploratory same-prompt, same-arm concept-state permutation: one derangement reused for every method.
 rng=np.random.default_rng(SEED);perm=rng.permutation(len(ev))
 while np.any(perm==np.arange(len(ev))):perm=rng.permutation(len(ev))
 for method in ['oracle','nla']:
  for a in arms:
   hits[method+'_shuffled',a]=np.array([c in obs[ev[perm[i]],p,a,method,'closed']['top5'] for i,c in enumerate(ev) for p in pids],float).reshape(shape)
 gates={a:{'n':400,'invisible':sum(bool(beh[c,p,a]['invisible']) for c in ev for p in pids),'max_kl':max(beh[c,p,a]['kl'] for c in ev for p in pids),'changed_answers':sum(beh[c,p,a]['natural']['tokens']!=beh[c,p,a]['edited']['tokens'] for c in ev for p in pids)} for a in arms}
 comparisons={};verdicts={};ps=[];pnames=[]
 for method in ['oracle','nla']:
  comparisons[method]={}
  for label,other,threshold in [('prompt_only',hits['prompt_only','concept'],.1),('matched_random',hits[method,'random'],0),('shuffled_state',hits[method+'_shuffled','concept'],0),('linear_same_site',hits['linear_L'+('44' if method=='oracle' else '42'),'concept'],0),('cosine_same_site',hits['cosine_L'+('44' if method=='oracle' else '42'),'concept'],0)]:
   comparisons[method][label]=interval(hits[method,'concept']-other,weights,threshold)
   if label in ['prompt_only','matched_random']:ps.append(comparisons[method][label]['exploratory_p']);pnames.append(method+':'+label)
  v=comparisons[method];verdicts[method]=S.verdict(v['prompt_only']['ci95'],v['matched_random']['ci95'],gates_ok=gates['concept']['invisible']==400,complete=valid[method,'concept']==400)
 for method in ['oracle','nla','prompt_only','labelled_probe','transfer_probe']:
  auroc[method]={}
  for a in ['concept','random']:
   x=[obs[c,p,a,method,'detection']['score'] for c in ev for p in pids];y=[obs[c,p,'placebo',method,'detection']['score'] for c in ev for p in pids]
   auroc[method][a]=float(roc_auc_score([1]*400+[0]*400,x+y))
 for method in ['oracle','nla','prompt_only']:
  open_rows[method]={a:{'n':400,'valid_eos':sum(bool(obs[c,p,a,method,'open']['valid']) for c in ev for p in pids),'specific_hit_rate':None,'reason':'Registered blinded semantic judge not run: CPU-only analysis; no replacement lexical scorer.'} for a in arms}
 result={'truth_join_started_at':joined_at,'panel_pinned_at':manifest['pinned_at'],'amendment':'8da8ae4d','n_concepts':20,'n_prompts':20,'n_corpora':len(set(corpora)),'n_families':5,'bootstrap_seed':SEED,'bootstrap_draws':10000,'bootstrap_schemes':['within-concept paired item','corpus/concept crossed shared prompt','corpus/concept crossed family/prompt'],'verdicts':verdicts,'invisibility':gates,'closed_rates':{m:{a:float(hits[m,a].mean()) for a in arms} for m,a in hits if a=='concept'},'contrasts':comparisons,'exploratory_bh_family':dict(zip(pnames,map(float,bh(ps)))),'exploratory_shuffled_concept_mapping':{c:ev[perm[i]] for i,c in enumerate(ev)},'detection_auroc':auroc,'open_vocabulary':open_rows,'closed_valid_counts':{m:{a:valid[m,a] for a in arms} for m in ['oracle','nla','prompt_only','jlens','labelled_probe']},'omnibus_bonferroni_pass':gates['concept']['invisible']==400 and any(comparisons[m]['prompt_only']['ci975'][0]>.1 and comparisons[m]['matched_random']['ci975'][0]>0 for m in ['oracle','nla'])}
 (out/'RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'verdicts':verdicts,'gates':gates,'closed_rates':result['closed_rates'],'truth_join_started_at':joined_at}))

if __name__=='__main__':main()
