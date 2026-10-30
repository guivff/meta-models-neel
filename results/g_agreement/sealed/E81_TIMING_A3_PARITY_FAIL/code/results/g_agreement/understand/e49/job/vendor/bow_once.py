"""E49 pre-seal CPU BOW build QA, once per immutable draft revision."""
import argparse,json,os
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from freeze_bank import sha,dump,HERE

def counts(records,vocabulary=None):
 if vocabulary is None:vocabulary={t:i for i,t in enumerate(sorted({t for r in records for t in r['ids']}))}
 indices=[];data=[];indptr=[0]
 for r in records:
  c=Counter(r['ids'])
  for t,n in sorted(c.items()):
   if t in vocabulary:indices.append(vocabulary[t]);data.append(n)
  indptr.append(len(indices))
 return csr_matrix((data,indices,indptr),shape=(len(records),len(vocabulary)),dtype=float),vocabulary

def score_row(records):
 dev=[x for x in records if x['split']=='dev'];test=[x for x in records if x['split']=='test']
 X,vocab=counts(dev);Z,_=counts(test,vocab)
 model=LogisticRegression(C=1,penalty='l2',solver='liblinear',random_state=20261026,max_iter=2000)
 model.fit(X,[x['label'] for x in dev]);scores=model.decision_function(Z)
 return {'test_auroc':float(roc_auc_score([x['label'] for x in test],scores)),'dev_items':len(dev),'test_items':len(test),'vocabulary':vocab,'coefficients':model.coef_.tolist(),'intercept':model.intercept_.tolist(),'test_scores':dict(zip([x['id'] for x in test],scores.tolist()))}

def main():
 p=argparse.ArgumentParser();p.add_argument('--draft',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if (HERE/'BANK_FREEZE.lock').exists():raise ValueError('BOW QA forbidden after input-bank freeze')
 seal=json.loads((a.draft/'DRAFT_MANIFEST.json').read_text())
 if seal.get('status')!='DRAFT_NOT_FROZEN' or seal['items']!=2688:raise ValueError('complete 16-row draft required')
 for n,h in seal['files'].items():
  if sha(a.draft/n)!=h:raise ValueError('bank hash mismatch')
 for n,h in seal['source_files'].items():
  if sha(HERE/n)!=h:raise ValueError('frozen source changed')
 # Keep every attempt; generator fixes require a new draft, never overwrite an old QA run.
 lock=a.draft/'BOW_ATTEMPT.lock';fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 os.write(fd,json.dumps({'code_sha256':sha(__file__),'output':str(a.out.resolve())}).encode());os.close(fd)
 a.out.mkdir(parents=True,exist_ok=False)
 records=json.loads((a.draft/'items.PRIVATE.json').read_text());validation=json.loads((a.draft/'VALIDATION.json').read_text());metrics={};fits={}
 for row in seal['row_order']:
  result=score_row([x for x in records if x['feature']==row]);fits[row]=result
  tracked=validation[row]['spec']['kind']!='descriptor'
  metrics[row]={'test_auroc':result['test_auroc'],'tracked':tracked,'gate_pass':not tracked or result['test_auroc']<=.65}
 dump(a.out/'FITS.PRIVATE.json',fits);dump(a.out/'METRICS.json',metrics)
 dump(a.out/'BOW_SEAL.json',{'complete':True,'stage':'PRESEAL_BUILD_QA','draft_manifest_sha256':sha(a.draft/'DRAFT_MANIFEST.json'),'code_sha256':sha(__file__),'lock_sha256':sha(lock),'files':{n:sha(a.out/n) for n in ['FITS.PRIVATE.json','METRICS.json']}})
 print('BOW gate sealed:',sha(a.out/'BOW_SEAL.json'))
if __name__=='__main__':main()
