"""Separate E96 bank transport: §212 cap and §217 terminal length/global402 pause.

Frozen judge/scoring/rubrics remain unchanged; executed runtime is archived.
"""
import hashlib,json,datetime,shutil
from pathlib import Path
from decimal import Decimal
from . import judge as frozen
from .resume_transport import runtime as transport_runtime
from .reconstructor_check import digest,write
SHARED_QUEUE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue')
PAUSE=SHARED_QUEUE/'PAUSED_402.json'
PACER_PINS={'/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/projects/g_agreement/understand/blind_judge/parallel_funded.py': 'ffdf2186a9f1b4b312b2c05916732c4c8ce80f30fe0d00cf5a147be5a32f3649', '/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/projects/g_agreement/understand/blind_judge/funded_queue.py': '33ea40c2a2a5d8e6c78e38c16363e73549bbdfd657b8e35d0f2fbbdf64e99b86'}

def shared_pacer():
 # Execute only the unchanged pacing/transport functions from the pinned owner source.
 # Avoid importing unrelated E101 scientific packages into this E96 process.
 import ast,fcntl,os,time,contextlib,types
 from projects.g_agreement.readerbench.io import read,write as owner_write
 from projects.g_agreement.readerbench.scoring import require
 for name,h in PACER_PINS.items():
  if digest(name)!=h:raise ValueError('shared pacer source changed; reverify before sends')
 source=next(n for n in PACER_PINS if n.endswith('/parallel_funded.py'))
 tree=ast.parse(Path(source).read_text());names={'pacing_lock','initial_pacing','claim_slot','rate_limited','eligible_429','patch_api'}
 nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in names]
 if {n.name for n in nodes}!=names:raise ValueError('shared pacing function inventory')
 state=types.SimpleNamespace(CACHE=SHARED_QUEUE)
 ns=dict(hashlib=hashlib,fcntl=fcntl,os=os,time=time,contextmanager=contextlib.contextmanager,read=read,write=owner_write,require=require,f=state,MAX_429_RETRIES=4)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),source+'[pacing functions only]','exec'),ns)
 return types.SimpleNamespace(**ns)

def budget(path,packet_sha):
 d=json.loads(Path(path).read_text());cap=Decimal(str(d['allocation_usd']));prior=Decimal(str(d['prior_E96_actual_usd']));total=Decimal(str(d['global_judging_committed_including_e96_usd']))
 if d.get('issuer')!='I-4' or d.get('bank')!='E96' or not d.get('verified') or d.get('packet_seal_sha256')!=packet_sha:raise ValueError('current separate bank receipt binding')
 if not all(x.is_finite() for x in [cap,prior,total]) or not 0<cap or prior<0 or cap+prior>120 or not cap<=total<=1000:raise ValueError('registered E96 cumulative120/global1000 caps')
 if not d.get('global_evidence') or not d.get('allocation_authority'):raise ValueError('allocation provenance')
 return cap

def audit(saved,protocol):
 if saved.get('http_status')==402:
  PAUSE.parent.mkdir(parents=True,exist_ok=True)
  if not PAUSE.exists():write(PAUSE,{'status':'PAUSE_ALL_BANKS_FUNDING_REQUIRED','bank':'E96_SLOT1_SEPARATE','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'response_sha256':hashlib.sha256(json.dumps(saved,sort_keys=True).encode()).hexdigest(),'resume':'confirmed funding plus exactsavedrefusal/charge reconciliation; no blind resend'})
  raise RuntimeError('HTTP402: all banks pause; funding/evidence reconciliation required')
 body=saved.get('response') or {};choices=body.get('choices') or []
 if saved.get('http_status')==200 and len(choices)==1 and choices[0].get('finish_reason')=='length':
  cost=Decimal(str((body.get('usage') or {}).get('cost')))
  if body.get('provider')!=protocol.PROVIDER_NAME or body.get('model') not in (protocol.MODEL,protocol.MODEL+'-001') or not cost.is_finite() or cost<0:raise ValueError('length route or charge unverified')
  return {'model':body['model'],'provider':body['provider'],'cost_usd':str(cost),'terminal_length':True}
 return frozen.response_audit(saved,protocol)

def judge_terminal(items,send):
 results={}
 for start in range(0,len(items),4):
  for row in send(items[start:start+4],0):results[row['id']]=dict(row,attempts=0)
 for item in items:
  row=results[item['id']]
  if row['status']=='KEPT' or row.get('terminal_reason')=='charged_length':continue
  for attempt in (1,2):
   row=dict(send([item],attempt)[0],attempts=attempt);results[item['id']]=row
   if row['status']=='KEPT' or row.get('terminal_reason')=='charged_length':break
  if row['status']!='KEPT':row.update(status='UNPARSEABLE',code=None)
 return [results[x['id']] for x in items]

def adapt_terminal(terminal,items):
 special={x['id']:x for x in terminal if x.get('terminal_reason')=='charged_length'}
 ordinary=[x for x in terminal if x['id'] not in special];ordinary_items=[x for x in items if x['id'] not in special]
 flat,attempts=frozen.adapt_grid(ordinary,ordinary_items);f={x['id']:x for x in flat};a={x['id']:x for x in attempts}
 for key,row in special.items():
  if row['status']!='UNPARSEABLE' or row['code'] is not None or row['attempts'] not in (0,1,2):raise ValueError('terminal length identity')
  f[key]={'id':key,'category':'UNPARSEABLE','values':[],'evidence':''};a[key]={'id':key,'status':'UNPARSEABLE','attempts':row['attempts'],'terminal_reason':'charged_length','retried_after_length':False}
 return [f[x['id']] for x in items],[a[x['id']] for x in items]

def runtime():
 _,original,source=transport_runtime()
 old="ledger=ROOT/'cache/g_agreement/e96/judging_120'";new="ledger=ROOT/'cache/g_agreement/e96/separate_slot1/ledger'";assert source.count(old)==1;source=source.replace(old,new)
 old="audit=response_audit(saved_response,protocol)";assert source.count(old)==1;source=source.replace(old,"audit=section217_audit(saved_response,protocol)")
 old="if result['status']=='OK':return result['value']";assert source.count(old)==1;source=source.replace(old,"if audit.get('terminal_length'):return [dict(id=x['id'],status='UNPARSEABLE',code=None,terminal_reason='charged_length') for x in batch]\n                        "+old)
 old="result=client.one(stage,batch);rid=result['id'];";assert source.count(old)==1;source=source.replace(old,"if global_pause.exists():raise RuntimeError('global402pause active; no send')\n                        "+old)
 old="if not response.exists() or client.latch.is_set():raise RuntimeError('transport/budget/unresolved stop; no resend')";assert source.count(old)==1;source=source.replace(old,"if response.exists() and json.loads(response.read_text()).get('http_status')==402:section217_audit(json.loads(response.read_text()),protocol)\n                        "+old)
 ns={'__name__':__name__+'._runtime','__package__':frozen.__package__,'__file__':frozen.__file__};exec(compile(source,str(frozen.__file__)+'[separate217 transport]','exec'),ns)
 ns.update(allocation=budget,section217_audit=audit,judge=judge_terminal,adapt_grid=adapt_terminal,global_pause=PAUSE)
 # Join existing shared FIFO pacing and account402latch; no cross-bank request-duration lock.
 load=ns['route_modules']
 def route(route):
  api,privacy,protocol,io=load(route);shared_pacer().patch_api(api,io,'E96_SLOT1_SEPARATE');return api,privacy,protocol,io
 ns['route_modules']=route
 return ns['run'],original,source

def run(packet,allocation,receipt_dir):
 if PAUSE.exists():raise RuntimeError('global402pause active')
 seal=json.loads((packet/'PACKET_SEAL.json').read_text())
 if seal['scope']['mode']!='separate_slot1_17920':raise ValueError('separate-only scope')
 if (packet.parent/'judgments/JUDGMENT_SEAL.json').exists():raise ValueError('sealed judgments never replayed')
 if digest(frozen.__file__)!=seal['code_files']['projects/g_agreement/e96/judge.py']:raise ValueError('frozen judge changed')
 f,original,source=runtime();receipt_dir.mkdir(parents=True,exist_ok=True);out=packet.parent/'judgments';out.mkdir(exist_ok=True)
 doc={'authority':'§212amend2/§217','packet_seal_sha256':digest(packet/'PACKET_SEAL.json'),'allocation_sha256':digest(allocation),'original_judge_sha256':hashlib.sha256(original.encode()).hexdigest(),'executed_runtime_sha256':hashlib.sha256(source.encode()).hexdigest(),'driver_sha256':digest(__file__),'patches':['isolated output ledger','returned response ID audit','bank cumulative120/global1000 receipt','charged length terminal UNPARSEABLE without resend','global402pause check before every send; unknown errors stop'],'shared_pacer_sources':PACER_PINS,'scientific_settings_unchanged':True}
 write(receipt_dir/'SOURCE_RECEIPT.json',doc);(receipt_dir/'EXECUTED_JUDGE_RUNTIME.py').write_text(source)
 for name,h in PACER_PINS.items():
  if digest(name)!=h:raise ValueError('shared source changed')
  shutil.copy2(name,out/('SHARED_EXECUTED_'+Path(name).name))
 for p in [receipt_dir/'SOURCE_RECEIPT.json',receipt_dir/'EXECUTED_JUDGE_RUNTIME.py',Path(__file__),Path(__file__).with_name('separate_watch217.py')]:shutil.copy2(p,out/p.name)
 return f(packet,allocation)
