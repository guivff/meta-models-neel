import argparse,concurrent.futures,os,time,subprocess
from collections import Counter
from . import io as I,protocol as P,api
from ..e10 import privacy as route_privacy

def jobs():
 result={}
 for r in I.rows(I.CACHE/'pool.private.jsonl'):
  item={'question':P.QUESTIONS[r['feature']]['question'],'readout':r['raw']};wire=P.payload('code',[item]);P.check_wire('code',[item],wire);result[I.digest(I.canonical(wire))]=item
 return result

def freeze():
 j=jobs();I.save(I.OUT/'JUDGE_PROMPT.json',{'system':P.SYSTEM,'questions':P.QUESTIONS,'wire':P.payload('code',[{'question':'PROPERTY_QUESTION','readout':'GENERATED_READOUT'}])})
 names=[x.relative_to(I.ROOT).as_posix() for x in __import__('pathlib').Path(__file__).parent.glob('*.py')]+['results/g_agreement/understand/e13/JUDGE_PROMPT.json','results/g_agreement/understand/e13/POOL_MANIFEST.json']
 plan={'status':'FROZEN_BEFORE_E13_CODING','seed':I.SEED,'section':101,'api_cap_usd':5,'model':P.MODEL,'provider':P.PROVIDER,'reasoning':'minimal','workers':8,'retries':0,'batch_size':1,'unique_requests':len(j),'full_call_reservation_usd':str(sum((api.upper(P.payload('code',[v])) for v in j.values()),api.Decimal(0))),'metrics':'Primary test sample only. Mention rate per reader/row and Wilson95; among mentions, binary-value accuracy/Wilson95 (UNSPECIFIED/CONFLICT incorrect). Missing codes excluded from rates, counts explicit, missing-as-no/yes bounds descriptive. NLA-Oracle paired item bootstrap2000/seed20261024 over states with valid codes for both. Conditional-accuracy difference bootstrap keeps same sampled items; unavailable if either side has no mentions or fewer than1900/2000 draws have mentions for both readers. Keyword regex rate and judge/script disagreement counts as cross-check only. No new confirmatory thresholds. Only two W1 rows; no general claim over16 or §84.','validation':'Single-readout schema/mention-value validation; no retry/repair. Exact evidence is an audit flag, not an exclusion criterion for typed primary codes, to avoid E10 quote-validation attrition. Each response independent. No one-to-one matching stage.','sealing':'Coding and keyword flags sealed before metric/value join. Authorized row/value-stratified sampling is the only pre-code use of labels. No source prompts/labels/reader names/paths sent. Fixed questions give both possible values, never the true one.','frozen_files':{n:I.sha(I.ROOT/n) for n in sorted(names)}}
 if api.Decimal(plan['full_call_reservation_usd'])>api.CAP:raise RuntimeError('full request bound above $5; no send')
 I.save(I.OUT/'PLAN.json',plan);print({k:plan[k] for k in ['unique_requests','full_call_reservation_usd']})

def verify():
 plan=I.read(I.OUT/'PLAN.json');m=I.read(I.OUT/'POOL_MANIFEST.json')
 for n,h in plan['frozen_files'].items():
  if I.sha(I.ROOT/n)!=h:raise RuntimeError('frozen code/prompt changed')
 for n,h in m['files'].items():
  if I.sha(I.CACHE/n)!=h:raise RuntimeError('sample changed')
 subprocess.run(['git','cat-file','-e','HEAD:results/g_agreement/understand/e13/PLAN.json'],cwd=I.ROOT,check=True)
 return plan

def execute():
 verify();route_privacy.check_route(os.environ['OPENROUTER_API_KEY']);j=jobs();c=api.Client(I.CACHE/'api',os.environ['OPENROUTER_API_KEY']);result={};last=time.monotonic()
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
  futures={executor.submit(c.one,'code',[v]):k for k,v in j.items()}
  for f in concurrent.futures.as_completed(futures):
   result[futures[f]]=f.result()
   if time.monotonic()-last>20:print('code',len(result),'/',len(j),c.ledger.summary(),flush=True);last=time.monotonic()
 coded=[]
 for r in I.rows(I.CACHE/'pool.private.jsonl'):
  wire=P.payload('code',[{'question':P.QUESTIONS[r['feature']]['question'],'readout':r['raw']}]);v=result[I.digest(I.canonical(wire))];coded.append({'case_id':r['case_id'],'request_hash':v['id'],'status':v['status'],'reason':v.get('reason'),'code':v.get('value'),'keyword':P.keyword(r['feature'],r['raw'])})
 I.save(I.CACHE/'codes.blind.json',coded);I.save(I.OUT/'CODING_SEAL.json',{'status':'CODES_AND_KEYWORD_FLAGS_SEALED_BEFORE_METRIC_JOIN','sha256':I.sha(I.CACHE/'codes.blind.json'),'file':'cache/g_agreement/understand/e13/codes.blind.json','at':time.time(),'api_cost':c.ledger.summary()});print('CODING_SEALED',Counter(r['status'] for r in coded),c.ledger.summary(),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','execute']);a=p.parse_args();freeze() if a.action=='freeze' else execute()
