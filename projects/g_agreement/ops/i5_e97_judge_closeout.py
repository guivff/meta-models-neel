"""Complete-only E97 administrative verification/publication. No statistics.
Original diagnostic replies remain immutable and never become scored content.
"""
from pathlib import Path
from types import SimpleNamespace
from decimal import Decimal
import json,hashlib,shutil,datetime,re,os,sys
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.understand.blind_judge.transport217c2 import eligible
ROOT=Path.cwd();Q=ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E97';J=Q/'judgments'
PUB=ROOT/'results/g_agreement/sealed/E97_JUDGMENTS_COMPLETE';RECEIPT=ROOT/'results/g_agreement/understand/e97/I5_JUDGMENT_COMPLETE_CLOSEOUT.json'
P=SimpleNamespace(PROVIDER_NAME='Google',MODEL='google/gemini-3.1-flash-lite')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
def request_id(path):
 name=Path(path).name
 if not name.endswith('.response.json'):raise ValueError('exact saved-response suffix required')
 return name[:-len('.response.json')]
def terminal_gate(s):
 if not(s.get('bank')=='E97'and s.get('primary_records')==6668 and s.get('old_rubric_records')==1667 and s.get('route_verified')is True and s.get('redaction_audit_complete')is True and s.get('transport217c2_finalized')is True and s.get('transport217c2_authority')=='3f9842e1af11940fc9fdc4ff6507773c195f74f6' and len(set(s.get('redacted_opaque_ids',[])))==227):raise ValueError('full terminal/custody/transport-finalized grid required')
def diagnostic_kind(saved):
 if eligible(saved,P):return 'CLARIFICATION2_EXPLICIT_ZERO_PROVIDER_ERROR'
 body=saved.get('response',{})
 if saved.get('http_status')==429 and isinstance(body,dict)and not body.get('id')and not body.get('choices'):return 'ORIGINAL_HTTP429_NO_GENERATION'
 raise ValueError('unknown/charged/unapproved diagnostic envelope')
def main():
 assert not PUB.exists()and not RECEIPT.exists(),'no closeout replay'
 compute=ROOT/'results/g_agreement/compute.jsonl';rows=[json.loads(l)for l in compute.read_text().splitlines()if l.strip()];assert not any(x.get('event')=='judge_bank_closed'and x.get('bank')=='E97'for x in rows),'existing closeout booking; finish manually'
 s=read(J/'JUDGMENT_SEAL.json');terminal_gate(s)
 for n,h in s['files'].items():assert sha(J/n)==h,n
 cost=read(J/'COST.json');assert Decimal(cost['unresolved_reserve_usd'])==0,'unresolved charges: preserve all, no financial closeout';assert Decimal(cost['actual_usd'])<=15
 packet=ROOT/'cache/g_agreement/understand/e97/judge_copy_v1';assert sha(packet/'INPUT_SEAL.json')==s['input_sha256']
 for n,h in read(packet/'INPUT_SEAL.json')['files'].items():assert sha(packet/n)==h,n
 inv=ROOT/'cache/g_agreement/understand/e97/judge_inventory_v1';cpu=read(ROOT/'results/g_agreement/understand/e97/I5_JUDGING_INVENTORY_CPU_RECEIPT.json')
 for n,h in cpu['files'].items():assert sha(inv/n)==h,n
 mapping=read(inv/'MAPPING.PRIVATE.json')
 for x in mapping:assert sha(x['source_path'])==x['source_sha256'],'original native hash'
 ids={x['id']for x in mapping};assert len(mapping)==len(ids)==6720
 selected={x['id']for x in read(inv/'REGEX_CLASSIFICATIONS.PRIVATE.json')if x['unresolved']};assert len(selected)==6668
 primary=read(J/'PRIMARY.json');old=read(J/'ORIGINAL.json');assert len(primary)==6668 and {x['id']for x in primary}==selected;assert len(old)==1667 and {x['id']for x in old}==set(read(inv/'ORIGINAL_IDS.PRIVATE.json'))
 audit=read(packet/'PATH_REDACTION_AUDIT.PRIVATE.json');assert set(s['redacted_opaque_ids'])=={x['id']for x in audit['affected']} and len(audit['affected'])==227
 original=ROOT/'results/g_agreement/understand/blind_judge/e97_bank/SOURCE_SEAL.json';assert sha(original)==s['source_seal_sha256']
 transport=ROOT/'results/g_agreement/understand/blind_judge/transport217c2/SOURCE_SEAL.json';assert sha(transport)==s['transport217c2_source_seal_sha256']=='df51bf3af115c91ddd03611c7a9c93db53670658850d2a27b5975d0ea1e978c8'
 oldfiles,newfiles=read(original)['files'],read(transport)['files'];assert all(oldfiles[n]==newfiles[n]for n in set(oldfiles)&set(newfiles)),'source overlap mismatch'
 sourcefiles=oldfiles|newfiles
 for n,h in sourcefiles.items():assert sha(ROOT/n)==h,n
 ledger=[json.loads(l)for l in(Q/'ledger/ledger.jsonl').read_text().splitlines()if l.strip()];reserved={};settled={};times={}
 for x in ledger:
  if x['event']=='reserve':assert x['id']not in reserved;reserved[x['id']]=Decimal(x['usd']);times[x['id']]=x['at']
  else:assert x['event']=='settle'and x['id']in reserved and x['id']not in settled;settled[x['id']]=Decimal(x['usd']);assert settled[x['id']]<=reserved[x['id']]
 assert set(reserved)==set(settled)and sum(settled.values())==Decimal(cost['actual_usd'])
 responses=sorted((Q/'ledger').glob('E97_*_attempt*/*.response.json'));assert responses
 byid={request_id(p):p for p in responses};assert len(byid)==len(responses)
 route=read(J/'ROUTE_AUDIT.json');assert route['routes']and all(x['tag']=='google-vertex/global'and x['provider_name']=='Google'and x['model_id']==P.MODEL for x in route['routes'])
 assert sha(Q/'ledger/route/OPENROUTER_PRIVACY_PROOF.json')==route['privacy_proof_sha256']
 chains=read(J/'TRANSPORT217C2.json')
 seen=set()
 for x in route['requests']:
  assert x['provider']=='Google'and x['model']in(P.MODEL,P.MODEL+'-001')and x['request_id']in byid
  path=byid[x['request_id']];assert sha(path)==x['response_sha256']and Decimal(x['cost_usd'])==settled[request_id(path)]
  saved=read(path);body=saved['response'];assert saved['http_status']==200 and body['provider']==x['provider']and body['model']==x['model']
  finish=body['choices'][0]['finish_reason']
  if eligible(saved,P):assert x.get('terminal_unparseable')is True and x.get('transport_exhausted')is True and any(e.get('exhausted')and e['attempts'][-1]['request_id']==request_id(path) for e in chains.values()),'partial error must not be scored'
  else:assert finish in ('stop','length')
  if finish=='length':assert x.get('terminal_unparseable')is True
  assert request_id(path) not in seen;seen.add(request_id(path))
 chainids=set()
 for event in chains.values():
  attempts=event['attempts'];assert 1<=len(attempts)<=3 and [x['transport_attempt']for x in attempts]==list(range(len(attempts)))
  for i,a in enumerate(attempts):
   path=byid[a['request_id']];assert sha(path)==a['response_sha256'];chainids.add(request_id(path))
   if a['eligible_uncharged_provider_error']:assert eligible(read(path),P)and settled[request_id(path)]==0
   if i:assert times[request_id(path)]-byid[attempts[i-1]['request_id']].stat().st_mtime>=30,'actual retry backoff'
  if event['exhausted']:assert len(attempts)==3 and attempts[-1]['eligible_uncharged_provider_error']
 diagnostics={}
 for rid,path in byid.items():
  if rid in seen:continue
  kind=diagnostic_kind(read(path));assert settled[request_id(path)]==0
  if kind.startswith('CLARIFICATION2'):assert rid in chainids
  diagnostics[rid]=dict(kind=kind,response_sha256=sha(path))
 assert {request_id(p) for p in responses}==set(settled),'all physical requests have original saved replies'
 members={**{'judgments/'+n:J/n for n in s['files']},'judgments/JUDGMENT_SEAL.json':J/'JUDGMENT_SEAL.json','ledger/ledger.jsonl':Q/'ledger/ledger.jsonl','source/ORIGINAL_SOURCE_SEAL.json':original,'source/TRANSPORT_SOURCE_SEAL.json':transport,'code/closeout.py':Path(__file__).resolve()}
 members.update({'raw/'+str(p.relative_to(Q/'ledger')):p for p in responses});members.update({'source/'+n:ROOT/n for n in sourcefiles})
 pat=re.compile(rb'hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}');key=os.environ.get('OPENROUTER_API_KEY','').encode()
 for n,p in members.items():
  b=p.read_bytes();assert not pat.search(b),'credential-pattern audit required: '+n;assert not key or key not in b,'credential present'
 PUB.mkdir(parents=True)
 for n,p in members.items():
  dst=PUB/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst);assert sha(dst)==sha(p)
 first=min(responses,key=lambda p:p.stat().st_mtime_ns);now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 receipt=dict(status='VERIFIED_COMPLETE_E97_JUDGMENTS',at_utc=now,primary_records=6668,old_rubric_records=1667,native_records=6720,all_member_hashes_verified=True,route_privacy_verified=True,judgment_seal_sha256=sha(J/'JUDGMENT_SEAL.json'),transport_finalized=True,source_seal_sha256=sha(original),transport_source_seal_sha256=sha(transport),physical_requests=len(responses),diagnostic_responses=len(diagnostics),all_original_replies_preserved=True,actual_usd=cost['actual_usd'],unresolved_usd='0',allocation_usd=15,released_unused_allocation_usd=str(Decimal(15)-Decimal(cost['actual_usd'])),physical_cost_already_in_canonical_ledger=True,new_physical_charge_usd=0,first_judgment_output=dict(path=str(first),mtime_ns=first.stat().st_mtime_ns),scientific_analysis_run=False)
 dump(RECEIPT,receipt);dump(PUB/'CLOSEOUT.json',receipt);dump(PUB/'DIAGNOSTIC_RESPONSE_HASHES.json',diagnostics);dump(PUB/'SEAL.json',dict(status='COMPLETE_TERMINAL_PUBLICATION_NO_ANALYSIS',at_utc=now,files={str(p.relative_to(PUB)):sha(p)for p in PUB.rglob('*')if p.is_file()}))
 with compute.open('a')as f:f.write(json.dumps(dict(event='judge_bank_closed',bank='E97',at_utc=now,actual_usd=cost['actual_usd'],physical_cost_already_in_canonical_ledger=True,new_physical_charge_usd=0,released_unused_allocation_usd=receipt['released_unused_allocation_usd'],closeout_sha256=sha(RECEIPT)),sort_keys=True)+'\n')
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
