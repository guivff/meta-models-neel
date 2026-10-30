"""Exact800 control supplement; shared E73 ledger, frozen route, CPU default."""
import argparse,fcntl,hashlib,importlib.util,json,os,re,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
OLD=H.parent/'e73_judge_redacted_candidate';sys.path.insert(0,str(OLD));import dispatch as D
P=D.P;X=D.X;need=P.require;read=P.ordinary;decode=P.decode;sha=P.digest;save=D.save
RULING='25c32f25e0bbffcf7c87039131b67c6858d891ef';BRIEF='projects/g_agreement/BRIEF_UNDERSTAND.md'
JOB='E73_controls_judgments_once';STAGE='E73_controls_attempt'

def authority():
 raw=P.git_bytes(ROOT,RULING,BRIEF)
 need(b'[REDACTED_ADDRESS]' in raw and b'opaque ID and hash' in raw,'ADDRESS_RULING')
 return {'repo':str(ROOT),'commit':RULING,'path':BRIEF,'sha256':sha(raw)}

def transform(items):
 pats=X.patterns();out=[];records=[]
 for item in items:
  need(set(item)=={'id','rubric','readout'} and all(type(v)is str for v in item.values()),'WIRE_SCHEMA')
  need(not any(re.search(p,item[k])for p in pats for k in ('id','rubric')),'FORBIDDEN_METADATA')
  raw=item['readout'];need(not re.search(pats[0],raw),'KEY_TOKEN_STOP')
  spans=[]
  for i in range(1,5):
   for m in re.finditer(pats[i],raw):spans.append({'start':m.start(),'end':m.end(),'pattern_index':i,'matched_sha256':sha(m.group().encode()),'replacement':'[REDACTED_ADDRESS]' if i==4 else X.MARKER})
  spans.sort(key=lambda z:(z['start'],z['end'],z['pattern_index']))
  need(all(a['end']<=b['start']for a,b in zip(spans,spans[1:])),'OVERLAPPING_MATCH_STOP')
  text=raw
  for s in reversed(spans):text=text[:s['start']]+s['replacement']+text[s['end']:]
  out.append({**item,'readout':text})
  if spans:records.append({'opaque_id':item['id'],'original_sha256':sha(raw.encode()),'judge_copy_sha256':sha(text.encode()),'matches':spans})
 return out,records

def estimate(items):
 f=P.frozen_functions(ROOT);amount=P.Decimal(0)
 need(len(items)==800 and len({x['id']for x in items})==800,'EXACT800')
 for i in range(0,800,4):
  batch=items[i:i+4];wire=f.payload(batch,f.rubric,'E56',P.ROUTE);X.check_decoded(f,batch,wire,f.rubric);amount+=f.upper(wire)
 prior=P.ledger_committed();need(prior+amount<=P.CAP,'WHOLE_INITIAL_PASS_CAP')
 return {'n':800,'initial_pass_upper_usd':str(amount),'prior_committed_usd':str(prior),'hard_cap_usd':'5','analysis_allowed':False}

def validate():
 D.source_gate();a=authority();spec=decode(read(H/'PREPARED.json'))
 P.authority_gate({'path':str(ROOT/'results/g_agreement/i2/JUDGING_AUTHORITY.json'),'sha256':sha(read(ROOT/'results/g_agreement/i2/JUDGING_AUTHORITY.json'))},ROOT)
 need(spec['ruling']==a and spec['source_sha256']==sha(read(__file__)),'FROZEN_RUNTIME_SOURCE')
 for p,digest in spec['file_bindings'].items():need(sha(read(p))==digest,'CUSTODY_SOURCE_CHANGED')
 original=decode(read(H/'packet/WIRE_PACKET.json'));expected,records=transform(original)
 need(decode(read(H/'judge_copy/WIRE_PACKET.json'))==expected,'EXACT_MATCHED_SPAN_COPY')
 need(decode(read(H/'judge_copy/TRANSFORM.private.json'))=={'ruling':a,'n':800,'records':records,'sensitivity_excluding_affected_required':True},'REDACTION_RECEIPT')
 need(spec['ledger_root']==str(P.LEDGER.parent),'SHARED_LEDGER')
 proof=decode(read(spec['privacy_proof']['path']));need(sha(read(spec['privacy_proof']['path']))==spec['privacy_proof']['sha256'] and proof['private_input_output_logging'] is False and proof['openrouter_use_inputs_outputs'] is False,'PRIVACY_PROOF')
 result=estimate(expected);return spec,expected,result

def prepare():
 authority();original=decode(read(H/'packet/WIRE_PACKET.json'));changed,records=transform(original);result=estimate(changed)
 out=H/'judge_copy';out.mkdir(exist_ok=False,mode=0o700)
 save(out/'WIRE_PACKET.json',changed);save(out/'TRANSFORM.private.json',{'ruling':authority(),'n':800,'records':records,'sensitivity_excluding_affected_required':True})
 builder=decode(read(H/'BUILDER_SPEC.json'));paths=[H/'BUILDER_SPEC.json',ROOT/'results/g_agreement/i2/E73_CONTROL_NATIVE_BANK_SEAL.json',ROOT/'results/g_agreement/i2/JUDGING_AUTHORITY.json',H/'packet/BLIND_SEAL.json',H/'packet/WIRE_SEAL.json',H/'packet/JUDGE_PACKET.json',H/'packet/WIRE_PACKET.json',Path(builder['private_key']),out/'WIRE_PACKET.json',out/'TRANSFORM.private.json']
 paths +=[Path(builder[k])for k in ['bank_manifest','items','labels','gate','reader_index','go','forecast_proof']]
 pull=Path(builder['native'][0]['path']);paths +=list(pull.iterdir())
 for p in (H/'builder/projects/g_agreement/e73').glob('*.py'):
  relative=str(p.relative_to(H/'builder'));need(read(p)==P.git_bytes(ROOT,builder['adapter_commit'],relative),'COMMITTED_BUILDER_SOURCE');paths.append(p)
 privacy=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/.claude/worktrees/phase-r-integration-8abda6/cache/g_agreement/understand/e10/OPENROUTER_PRIVACY_PROOF.json')
 save(H/'PREPARED.json',{'schema':'i2-e73-controls-dispatch-v1','ruling':authority(),'source_sha256':sha(read(__file__)),'ledger_root':str(P.LEDGER.parent),'privacy_proof':{'path':str(privacy),'sha256':sha(read(privacy))},'file_bindings':{str(p):sha(read(p))for p in paths if p.is_file()},'initial_estimate':result,'redacted_records':len(records),'address_records':sum(any(m['pattern_index']==4 for m in r['matches'])for r in records),'analysis_allowed':False})
 print(json.dumps({'status':'CPU_PREPARED','redacted_records':len(records),**result}))

def run(proof,key):
 spec,items,admission=validate();ref=decode(read(proof));raw,_=P.committed(ref);freeze=decode(raw)
 need(freeze['source_sha256']==sha(read(__file__)) and freeze['prepared_sha256']==sha(read(H/'PREPARED.json')) and freeze['n']==800 and freeze['analysis_allowed'] is False,'COMMITTED_FREEZE')
 root=P.LEDGER.parent
 with (root/'DISPATCH.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);spec,items,admission=validate();job=root/JOB;need(not job.exists(),'NO_RESTART');need(bool(key),'KEY_UNAVAILABLE')
  job.mkdir(mode=0o700);save(job/'START.json',{'n':800,'prepared_sha256':sha(read(H/'PREPARED.json')),'runtime_proof':ref,'source_sha256':sha(read(__file__)),'analysis_allowed':False,'admission':admission,'started_epoch':time.time()})
  t=None
  try:
   import requests
   f=P.frozen_functions(ROOT);t,check=D.transport(ROOT,root,f.rubric,key,requests);check(key)
   # Existing account proof is exact; D.transport retains fixed ZDR/provider/cap.
   pp=root/'route/OPENROUTER_PRIVACY_PROOF.json';need(read(pp)==read(spec['privacy_proof']['path']),'ACCOUNT_PRIVACY_CHANGED')
   client,io=t.client,t.io
   def send(batch,attempt):
    io.digest=lambda value:hashlib.sha256(('E73-controls:'+str(attempt)+':'+value).encode()).hexdigest()
    stage=STAGE+str(attempt);result=client.one(stage,batch)
    if result['status']=='OK':return result['value']
    response=root/stage/(result['id']+'.response.json')
    need(response.exists() and not client.latch.is_set(),'TRANSPORT_STOP_NO_RESEND');r=io.read(response);body=r['response']
    need(r['http_status']==200 and body.get('provider')==P.ROUTE.PROVIDER_NAME and body.get('model')in(P.ROUTE.MODEL,P.ROUTE.MODEL+'-001') and body.get('usage',{}).get('cost')is not None and body['choices'][0].get('finish_reason')=='stop','ROUTE_COST_COMPLETION_STOP')
    try:json.loads(body['choices'][0]['message']['content'])
    except(ValueError,TypeError):return t.classify(batch,{},'E56')
    raise RuntimeError('UNEXPECTED_TRANSPORT_STOP')
   terminal=t.judge(items,send);need(len(terminal)==800 and [x['id']for x in terminal]==[x['id']for x in items],'TERMINAL_GRID')
   save(job/'JUDGMENTS.json',terminal);save(job/'RESULT_SEAL.json',{'status':'TERMINAL_CONTROLS_NO_ANALYSIS','n':800,'cost':client.ledger.summary(),'judgments_sha256':sha(read(job/'JUDGMENTS.json')),'start_sha256':sha(read(job/'START.json')),'ledger_sha256':sha(read(root/'ledger.jsonl')),'analysis_allowed':False,'completed_epoch':time.time()});print(json.dumps({'status':'COMPLETE','n':800,'cost':client.ledger.summary()}))
  except BaseException as e:
   save(job/'BLOCKED.json',{'status':'INCOMPLETE_NO_RESTART','error_type':type(e).__name__,'analysis_allowed':False,'cost':t.client.ledger.summary()if t else None});raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--dispatch',action='store_true');p.add_argument('--runtime-proof',type=Path);a=p.parse_args()
 try:
  if a.prepare:prepare()
  elif a.dispatch:run(a.runtime_proof,os.environ.get('OPENROUTER_API_KEY'))
  else:print(json.dumps({'status':'CPU_VALIDATED',**validate()[2]}))
 except BaseException as e:print(json.dumps({'status':'STOPPED','error_type':type(e).__name__}),file=sys.stderr);raise SystemExit(1)
