"""E89 fixed one-fit classifier. Commit code/plan before execution; CPU only."""
import hashlib,json,sys,time,subprocess,warnings
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from sklearn.pipeline import FeatureUnion,Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.exceptions import ConvergenceWarning
import joblib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];CACHE=ROOT/'cache/g_agreement/understand/e89'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def model():
 return Pipeline([('tfidf',FeatureUnion([('word',TfidfVectorizer(ngram_range=(1,2),min_df=2)),('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),min_df=2))])),('logistic',LogisticRegression(C=1,solver='liblinear',class_weight=None,max_iter=2000,tol=1e-4,random_state=20261028))])
def split_groups(rows,seed=20261028):
 groups=sorted({x['group']for x in rows});rng=np.random.default_rng(seed);train=set(rng.permutation(groups)[:len(groups)//2]);return ['train'if r['group']in train else'validation'for r in rows]
def outcomes(code):
 claims=code['claims'];assert code['generic']==(len(claims)==0)
 v=[c['verdict']for c in claims];assert all(x in ('SUPPORTED','CONTRADICTED','UNVERIFIABLE')for x in v)
 return {'contradicted':int('CONTRADICTED'in v),'no_supported':int('SUPPORTED'not in v)}
def weighted_auc(y,s,w):
 _,ix=np.unique(s,return_inverse=True);pos=np.bincount(ix,weights=w*y);neg=np.bincount(ix,weights=w*(1-y));p=pos.sum();n=neg.sum()
 if p==0 or n==0:return None
 return float(np.sum(pos*(np.cumsum(neg)-0.5*neg))/(p*n))
def metric(rows,target,draws=2000):
 kept=[r for r in rows if r['outcomes']is not None];y=np.array([r['outcomes'][target]for r in kept],dtype=int);s=np.array([r['score']for r in kept]);n=len(kept)
 result={'total':len(rows),'kept':n,'unparseable':len(rows)-n,'positive':int(y.sum()),'negative':int(n-y.sum()),'AUROC':None,'CI95':None,'undefined_bootstrap_replicates':0}
 if len(set(y))<2:result['status']='NOT EVALUABLE: outcome has fewer than two classes';return result
 result['AUROC']=float(roc_auc_score(y,s));groups=sorted({r['group']for r in kept});lookup={g:i for i,g in enumerate(groups)};gi=np.array([lookup[r['group']]for r in kept]);rng=np.random.default_rng(20261028);aucs=[]
 for _ in range(draws):
  counts=np.bincount(rng.integers(0,len(groups),size=len(groups)),minlength=len(groups));v=weighted_auc(y,s,counts[gi])
  if v is not None:aucs.append(v)
 result['undefined_bootstrap_replicates']=draws-len(aucs);result['CI95']=np.quantile(aucs,[0.025,0.975]).tolist()if aucs else None;result['status']='EVALUABLE';result['bootstrap_item_groups']=len(groups);return result
def cell(rows):return {k:metric(rows,k)for k in ('contradicted','no_supported')}
def verdict(c):
 a,b=c['contradicted'],c['no_supported']
 if a['AUROC']is None or b['AUROC']is None:return 'NOT EVALUABLE'
 if a['AUROC']>=.65 and a['CI95'][0]>.55 and b['AUROC']>=.65:return 'MET'
 if a['AUROC']<.55 and b['AUROC']<.55:return 'FALSIFIER MET'
 return 'NOT MET'
def main():
 started=time.time();plan=read(HERE/'RUN_PLAN.json');seal=read(HERE/'CODE_SEAL.json')
 for name,digest in seal['files'].items():
  path=ROOT/name;assert sha(path)==digest
  assert subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)==path.read_bytes(),'commit frozen code and plan first'
 for k in ('data','source_binding'):assert sha(plan[k]['path'])==plan[k]['sha256']
 for p,digest in read(plan['source_binding']['path']).items():assert sha(p)==digest,('source drift',p)
 data=read(plan['data']['path']);rows=data['training'];assert split_groups(rows)==[r['split']for r in rows]
 assert not {r['group']for r in rows}&{r['bank']+'|'+r['item_id']for r in data['test_text']}
 with (CACHE/'ONCE.json').open('x')as f:json.dump({'experiment':'E89','created_utc':datetime.now(timezone.utc).isoformat(),'code_seal_sha256':sha(HERE/'CODE_SEAL.json'),'plan_sha256':sha(HERE/'RUN_PLAN.json'),'status':'CLAIMED_NEVER_RESET'},f)
 fit=[r for r in rows if r['split']=='train'];validation=[r for r in rows if r['split']=='validation'];clf=model()
 print('E89 fixed fit starts; E67 judgments unopened',flush=True)
 with warnings.catch_warnings():
  warnings.simplefilter('error',ConvergenceWarning);clf.fit([r['text']for r in fit],[r['label']for r in fit])
 assert clf.named_steps['logistic'].classes_.tolist()==[0,1]
 validation_scores=clf.predict_proba([r['text']for r in validation])[:,1]
 validation_results={'overall':float(roc_auc_score([r['label']for r in validation],validation_scores)),'by_reader':{reader:float(roc_auc_score([r['label']for r in validation if r['reader']==reader],validation_scores[[r['reader']==reader for r in validation]]))for reader in ('oracle','nla')},'purpose':'held-out placebo-versus-real classification only; no tuning or refit'}
 features=clf.named_steps['tfidf'].get_feature_names_out();weights=clf.named_steps['logistic'].coef_[0];positive=np.argsort(-weights,kind='stable')[:30];negative=np.argsort(weights,kind='stable')[:30]
 top={'placebo_like':[{'ngram':str(features[i]),'coefficient':float(weights[i])}for i in positive],'real_like':[{'ngram':str(features[i]),'coefficient':float(weights[i])}for i in negative],'intercept':float(clf.named_steps['logistic'].intercept_[0]),'feature_count':len(features)}
 joblib.dump(clf,CACHE/'MODEL.joblib');dump(CACHE/'MODEL_SEAL.json',{'MODEL.joblib':sha(CACHE/'MODEL.joblib'),'trained_before_judgments_opened':True,'plan_sha256':sha(HERE/'RUN_PLAN.json')})
 print('Fit frozen and model sealed; scoring E67 text without fitting',flush=True)
 scores=clf.predict_proba([r['text']for r in data['test_text']])[:,1]
 # Save every P(placebo-like) before the first outcome file is opened.
 scored=[{k:v for k,v in r.items()if k!='text'}|{'score':float(s)}for r,s in zip(data['test_text'],scores)];dump(CACHE/'E67_SCORES_BEFORE_JUDGMENTS.PRIVATE.json',scored)
 judgments={}
 for wave,packets in data['judgments'].items():
  for packet,path in packets.items():
   grid=read(path);ids=[r['id']for r in grid];assert len(ids)==len(set(ids))
   for r in grid:
    assert r['status']in ('KEPT','UNPARSEABLE')
    if r['status']=='UNPARSEABLE':assert r['code']is None
    else:assert r['code']['id']==r['id']
    judgments[int(wave),int(packet),r['id']]=None if r['status']=='UNPARSEABLE'else outcomes(r['code'])
 assert set(judgments)=={(r['wave'],r['packet'],r['opaque_id'])for r in scored}
 for r in scored:r.update(outcomes=judgments[r['wave'],r['packet'],r['opaque_id']],group=r['bank']+'|'+r['item_id'])
 dump(CACHE/'ITEM_SCORES_AND_OUTCOMES.PRIVATE.json',scored)
 results={'experiment':'E89','authority':plan['authority'],'plan_sha256':sha(HERE/'RUN_PLAN.json'),'code_seal_sha256':sha(HERE/'CODE_SEAL.json'),'training_counts':plan['counts'],'training_item_groups':plan['train_item_groups'],'validation_item_groups':plan['validation_item_groups'],'excluded_for_E67_identity':plan['E67_identity_excluded_training_records'],'validation_placebo_vs_real_AUROC':validation_results,'primary':{},'by_wave':{},'by_bank':{},'by_cohort':{},'mismatched_diagnostic':{},'top_ngrams':top,'versions':plan['versions'],'fit_calls':1,'no_tuning':True,'GPU_hours':0}
 for reader in ('oracle','nla'):
  mine=[r for r in scored if r['reader']==reader and r['condition']=='matched'];c=cell(mine);results['primary'][reader]={'metrics':c,'R_H1':verdict(c)}
  for wave in (1,2):results['by_wave'][f'{reader}|wave{wave}']=cell([r for r in mine if r['wave']==wave])
  for bank in sorted({r['bank']for r in mine}):results['by_bank'][reader+'|'+bank]=cell([r for r in mine if r['bank']==bank])
  for cohort in sorted({r['cohort']for r in mine}):results['by_cohort'][reader+'|'+cohort]=cell([r for r in mine if r['cohort']==cohort])
  results['mismatched_diagnostic'][reader]=cell([r for r in scored if r['reader']==reader and r['condition']=='mismatched'])
 # Exact string overlap is reported as a limitation, not used to select records after fitting.
 train_hashes={hashlib.sha256(r['text'].encode()).hexdigest()for r in fit};test_unique={(r['wave'],r['reader'],r['bank'],r['item_id']):r for r in data['test_text']}
 results['exact_test_text_also_in_training']=sum(hashlib.sha256(r['text'].encode()).hexdigest()in train_hashes for r in test_unique.values())
 results['test_unique_readouts']=len(test_unique);results['wall_seconds']=time.time()-started;results['created_utc']=datetime.now(timezone.utc).isoformat()
 dump(HERE/'RESULTS.json',results);dump(HERE/'TOP_NGRAMS.json',top)
 lines=['# E89 placebo-likeness detector','','Fixed word(1–2)+char_wb(3–5) TF-IDF, logistic C=1; one pooled fit. Both E67 waves held out by source item; original bank analyses unchanged. Pooled E89 matched evaluation below, with wave/bank/cohort and mismatched diagnostics in RESULTS.json.','','| Reader | Outcome | n | Positive | AUROC | 95% item-bootstrap CI |','|---|---|---:|---:|---:|---|']
 for reader,block in results['primary'].items():
  for outcome,m in block['metrics'].items():lines.append(f"| {reader} | {outcome} | {m['kept']} | {m['positive']} | {m['AUROC']} | {m['CI95']} |")
  lines.append('');lines.append(f"{reader} R-H1: **{block['R_H1']}**.")
 lines+=['','Held-out training-domain placebo-versus-real validation AUROC: '+str(validation_results),'','Exact test readout strings also occurring in training: '+str(results['exact_test_text_also_in_training'])+'/'+str(results['test_unique_readouts'])+'. Source-item identities are disjoint; repeated generic strings are retained without content filtering. The real and placebo source banks, generation lengths and reader styles may provide domain cues. Associations do not establish detection of contradictions within a text. Bootstrap intervals condition on the single frozen trained model.','','Top placebo-like n-grams: '+', '.join(repr(x['ngram'])for x in top['placebo_like'][:15]),'','Top real-like n-grams: '+', '.join(repr(x['ngram'])for x in top['real_like'][:15]),'','All 60 coefficients and full per-bank/wave metrics are in TOP_NGRAMS.json and RESULTS.json. UNPARSEABLE judgments are excluded and counted per cell.']
 (HERE/'REPORT.md').write_text('\n'.join(lines)+'\n')
 dump(HERE/'RESULT_SEAL.json',{'experiment':'E89','files':{n:sha(HERE/n)for n in ('RESULTS.json','TOP_NGRAMS.json','REPORT.md')},'model_seal_sha256':sha(CACHE/'MODEL_SEAL.json'),'score_before_judgment_sha256':sha(CACHE/'E67_SCORES_BEFORE_JUDGMENTS.PRIVATE.json'),'item_score_outcomes_sha256':sha(CACHE/'ITEM_SCORES_AND_OUTCOMES.PRIVATE.json'),'claim_sha256':sha(CACHE/'ONCE.json')})
 print(json.dumps({'status':'COMPLETE','primary':results['primary'],'wall_seconds':results['wall_seconds']}),flush=True)
if __name__=='__main__':main()
