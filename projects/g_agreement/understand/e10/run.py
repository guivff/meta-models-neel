"""Frozen staged E10 pipeline. CPU/API only; stage seals precede reader joins."""
import argparse,concurrent.futures,time,subprocess,os
from collections import Counter,defaultdict
from . import io as I,protocol as P,api,privacy

def batches(items,n):return [items[i:i+n] for i in range(0,len(items),n)]
def extraction_jobs(blind):
 texts={};neighbors=defaultdict(set)
 for r in blind:
  a,b=[I.digest(r[k]) for k in ['READOUT_A','READOUT_B']]
  for k in ['READOUT_A','READOUT_B']:texts[I.digest(r[k])]=r[k]
  neighbors[a].add(b);neighbors[b].add(a)
 pending=sorted(texts);jobs=[]
 while pending:
  chosen=[];left=[]
  for h in pending:
   if len(chosen)<P.EXTRACT_BATCH and not any(h in neighbors[x] for x in chosen):chosen.append(h)
   else:left.append(h)
  jobs.append([{'id':h,'readout':texts[h]} for h in chosen]);pending=left
 return jobs

def seal(name,value):
 p=I.CACHE/(name+'.json');I.save(p,value)
 I.save(I.OUT/(name.upper()+'_SEAL.json'),{'file':'cache/g_agreement/understand/e10/'+p.name,'sha256':I.sha(p),'sealed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
 return value

def calls(client,stage,jobs,taxonomy=None):
 results=[];t=time.monotonic();last=t
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  futures=[pool.submit(client.one,stage,j,taxonomy) for j in jobs]
  for f in concurrent.futures.as_completed(futures):
   results.append(f.result())
   if time.monotonic()-last>=20:
    print(stage,len(results),'/',len(jobs),client.ledger.summary(),flush=True);last=time.monotonic()
 results.sort(key=lambda r:r['id']);seal(stage+'_responses',results)
 print(stage,'sealed',len(results),'calls',Counter(r['status'] for r in results),'seconds',round(time.monotonic()-t,1),client.ledger.summary(),flush=True)
 return {x['id']:x for r in results if r['status']=='OK' for x in r['value'].get('items',[])}

def verify():
 plan=I.read(I.OUT/'PLAN.json')
 for name,h in plan['frozen_files'].items():
  if I.sha(I.ROOT/name)!=h:raise RuntimeError('frozen implementation changed: '+name)
 m=I.read(I.OUT/'POOL_MANIFEST.json')
 for n,h in m['files'].items():
  if I.sha(I.CACHE/n)!=h:raise RuntimeError('pool changed')
 # Freeze must be in local history, not merely a working-file declaration.
 subprocess.run(['git','cat-file','-e','HEAD:results/g_agreement/understand/e10/PLAN.json'],cwd=I.ROOT,check=True,stdout=subprocess.DEVNULL)
 return m

def execute():
 m=verify();privacy.check_route(os.environ['OPENROUTER_API_KEY']);blind=I.rows(I.CACHE/'pool.blind.jsonl');client=api.Client(I.CACHE/'api',os.environ['OPENROUTER_API_KEY'])
 extract=calls(client,'extract',extraction_jobs(blind));seal('claims_blind',extract)
 matchitems=[];matched={};missing=[]
 for p in blind:
  a,b=[extract.get(I.digest(p[k])) for k in ['READOUT_A','READOUT_B']]
  if a is None or b is None:missing.append(p['pair_id']);continue
  x={'id':p['pair_id'],'a':[c['claim'] for c in a['claims']],'b':[c['claim'] for c in b['claims']]}
  if not x['a'] or not x['b']:matched[x['id']]={'id':x['id'],'matches':[]}
  else:matchitems.append(x)
 matched.update(calls(client,'match',batches(matchitems,P.MATCH_BATCH)));seal('matches_blind',matched)
 singles=[];coverage=[]
 for p in blind:
  pid=p['pair_id']
  if pid not in matched:continue
  counts={};shared=matched[pid]['matches']
  for side,k,idx in [('A','READOUT_A','a'),('B','READOUT_B','b')]:
   claims=extract[I.digest(p[k])]['claims'];used={x[idx] for x in shared};counts[side]=len(claims)
   for j,c in enumerate(claims):
    if j not in used:singles.append({'id':I.rank('claim',pid,side,j),'pair_id':pid,'side':side,'index':j,**c})
  coverage.append({'pair_id':pid,'claims_A':counts['A'],'claims_B':counts['B'],'matched':len(shared)})
 seal('one_sided_blind',singles);seal('pair_coverage_blind',coverage)
 sample=sorted(singles,key=lambda x:I.rank('taxonomy',x['id']))[:P.TAXONOMY_SAMPLE]
 if not sample:raise RuntimeError('no one-sided claims to cluster; report incomplete')
 t=client.one('taxonomy',[{'id':x['id'],'claim':x['claim']} for x in sample]);seal('taxonomy_response',t)
 if t['status']!='OK':raise RuntimeError('taxonomy missing; no repair, report incomplete')
 taxonomy=t['value']['types'];seal('taxonomy',taxonomy)
 typed=calls(client,'classify',batches([{'id':x['id'],'claim':x['claim']} for x in sorted(singles,key=lambda x:x['id'])],P.CLASSIFY_BATCH),taxonomy)
 seal('typed_blind',[{**x,'type':typed[x['id']]['type'] if x['id'] in typed else None} for x in singles])
 seal('cost',client.ledger.summary());print('ALL_STAGES_SEALED',flush=True)

def freeze():
 blind=I.rows(I.CACHE/'pool.blind.jsonl');jobs=extraction_jobs(blind)
 import pathlib
 names=[p.relative_to(I.ROOT).as_posix() for p in pathlib.Path(__file__).parent.glob('*.py')]
 prompt={'model':P.MODEL,'extract':P.EXTRACTION_SYSTEM,'match':P.MATCH_SYSTEM,'taxonomy':P.TAXONOMY_SYSTEM,'classify':P.CLASSIFY_SYSTEM,'schemas':{s:P.schema(s) for s in ['extract','match','taxonomy','classify']},'example_wire':P.payload('extract',[{'id':'OPAQUE','readout':'READOUT_DATA'}])}
 I.save(I.OUT/'PROMPTS.json',prompt);names+=['results/g_agreement/understand/e10/PROMPTS.json','results/g_agreement/understand/e10/POOL_MANIFEST.json']
 plan={'section':97,'experiment':'E10','status':'FROZEN_BEFORE_FIRST_E10_PAID_SEND','seed':I.SEED,'frozen_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'model':P.MODEL,'provider':'Google Vertex global only; no fallback; minimal reasoning; temperature 0','price_cap_per_million_usd':{'input':.25,'output':1.5},'public_endpoint_metadata_sha256':I.sha(I.CACHE/'gemini31_endpoints.json'),'gpu_h':0,'api_cap_usd':20,'privacy_amendment':'2026-10-24, before any inference: user approved Gemini 3.1 Flash Lite via Google Vertex through OpenRouter only, W1/S61 readouts and derived blinded claims; no source prompts, labels, keys or file paths. User increased hard cap to $20 before any inference. provider.data_collection=deny; provider.zdr=true; no fallbacks/redirects. Fail before inference unless exact model/provider occurs in ZDR inventory and OpenRouter own logging/use-of-inputs toggles are verified off. No scientific rule or pool changed.','model_substitution':'2026-10-24: approved Gemini 3.1 Flash Lite on Vertex global. Minimal reasoning (Gemini 3 thinking-level interface); max completion match4096/classify6144 to fit opaque IDs and strict JSON, before any scoring. Prompts, pool, batching, matching, clustering and selection unchanged.','workers':8,'retries':0,'extraction_unique_readouts':sum(map(len,jobs)),'extraction_calls':len(jobs),'extraction_all_call_reserves_usd':str(sum((api.upper(P.payload('extract',j)) for j in jobs),api.Decimal(0))),'extract':'Independent opaque text hashes; deduplicate identical raw strings globally. Batch 4; never include both nonidentical members of a pair in a batch. Exact evidence required. Whole invalid batch missing, no repair. No count cap on claims.','match':'Only pairs with both valid extractions; material equivalence; one-to-one; batch16. Zero claims on either side yields deterministic empty matching.','taxonomy':'Discover 3–12 content types on 512 one-sided claims by seeded hash; identities/source/sites/labels hidden; seal taxonomy before classification. Classify all remaining (including sample) once, batch64.','selection':'Rank types by total valid classified one-sided claims (ties by type id). For the top three, choose two eligible distinct pairs by number of claims of that type, descending; ties by seeded hash(example,type,pair). Reserve frozen two random pair IDs and avoid duplicates across all examples. No posthoc replacements for missing random annotations; report shortfalls. Exposure item excluded from examples.','coverage':'Report batch and pair failures, excluded W6, all stage missingness. No absent readout/extraction is a one-sided claim. No truth/correctness claim. All counts descriptive; no pass/fail, CI, or generalization.','interpretation':'Programme predicts complementary descriptive vs enacted content; no E10-specific numerical prediction registered. Claim count may reflect verbosity/style. Preserve raw output including markers and incomplete endings. Native sites confounded. Same text reused across cases and W1 repeat samples not independent.','frozen_files':{n:I.sha(I.ROOT/n) for n in sorted(names)}}
 I.save(I.OUT/'PLAN.json',plan);print({k:plan[k] for k in ['extraction_unique_readouts','extraction_calls','extraction_all_call_reserves_usd']})
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=['freeze','execute']);v=a.parse_args();freeze() if v.action=='freeze' else execute()
