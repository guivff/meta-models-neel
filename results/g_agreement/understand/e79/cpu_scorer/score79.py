"""CPU E79 Arm B scoring from selected next-token logits, no generation."""
import argparse,hashlib,json,math
from pathlib import Path
from frozen59 import continuation_aucs
HERE=Path(__file__).resolve().parent
CONDITIONS=('none','d_J','d_perp','random')
PAIRS={'format_plan':[['-','The']],'language_plan':[['Je','The'],['Le','The']]}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def score(records,private):
 keys=[(r['id'],r['condition']) for r in records]
 expected={(i,c) for i in private for c in CONDITIONS}
 if len(keys)!=len(set(keys)) or set(keys)!=expected:raise ValueError('Missing, duplicate, or unexpected item/condition')
 mapped=[]
 for r in records:
  item=private[r['id']];row=item['feature']
  if r['feature']!=row:raise ValueError('Wrong row')
  logits=r['pair_logits']
  if len(logits)!=len(PAIRS[row]) or any(len(p)!=2 or any(type(v) not in (float,int) or not math.isfinite(v) for v in p) for p in logits):raise ValueError('Invalid candidate logits')
  # E59 score for each one-token pair is log P(A)-log P(B).
  # The common full-vocabulary log-normalizer cancels exactly.
  mapped.append(dict(r,scores=[a-b for a,b in logits]))
 result={}
 for condition in CONDITIONS:
  selected=[r for r in mapped if r['condition']==condition]
  # Shape adapter only: unchanged frozen estimator expects reader/own-swap axes.
  legacy=[dict(r,reader=reader,arm=arm) for r in selected for reader in ('oracle','nla') for arm in ('own','swap')]
  v=continuation_aucs({'private':private,'continuation':legacy})['oracle']
  result[condition]={row:v[row]['own'] for row in PAIRS}
 return {'auroc':result,'behaviour_condition':{row:result['d_J'][row]>=result['none'][row]-.10 for row in PAIRS},'authority':'§196 clarification 1 b3c1e6d0','note':'Behaviour condition only; does not decide full R-C2 reporting criterion.'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--continuations',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--private-items',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 seal=read(HERE/'SCORER_SEAL.json')
 for path,h in seal['files'].items():
  if sha(HERE/path)!=h:raise ValueError('Scorer hash mismatch')
 if sha(a.continuations)!=a.sha256:raise ValueError('Input hash mismatch')
 binding=read(HERE/'INPUT_CONTRACT.json')
 if sha(a.private_items)!=binding['E59_private_items_sha256']:raise ValueError('Frozen E59 item hash mismatch')
 private={i['id']:i for i in read(a.private_items) if i['split']=='test' and i['feature'] in PAIRS}
 if len(private)!=168:raise ValueError('Expected 168 original test items')
 document=read(a.continuations)
 if document['schema']!='E79_ARM_B_NEXT_TOKEN_LOGITS_V1' or document['candidate_token_ids']!=binding['candidate_token_ids']:raise ValueError('Token contract mismatch')
 result=score(document['records'],private)
 a.out.mkdir(parents=True,exist_ok=False)
 (a.out/'METRICS.json').write_text(json.dumps(result,indent=2)+'\n')
 (a.out/'ANALYSIS_SEAL.json').write_text(json.dumps({'authority':'b3c1e6d0','input_sha256':a.sha256,'scorer_seal_sha256':sha(HERE/'SCORER_SEAL.json'),'private_items_sha256':sha(a.private_items),'files':{'METRICS.json':sha(a.out/'METRICS.json')}},indent=2)+'\n')
if __name__=='__main__':main()
