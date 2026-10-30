"""Administrative E98 terminal verification/publication; no outcome statistics."""
from pathlib import Path
import json,hashlib,shutil,datetime,re,os
from decimal import Decimal
ROOT=Path.cwd();Q=ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E98';J=Q/'judgments'
PUB=ROOT/'results/g_agreement/sealed/E98_JUDGMENTS_COMPLETE';RECEIPT=ROOT/'results/g_agreement/understand/e98/I5_JUDGMENT_COMPLETE_CLOSEOUT.json'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def verify(root,files):
 for n,h in files.items():assert sha(root/n)==h,n

def main():
 assert not PUB.exists() and not RECEIPT.exists(),'no closeout replay'
 seal=read(J/'JUDGMENT_SEAL.json');verify(J,seal['files']);assert seal['terminal'] and seal['route_verified']
 assert (seal['items'],seal['unique_items'],seal['primary_records'],seal['old_rubric_records'],seal['binary_items'],seal['nonbinary_items'])==(2184,2184,1785,447,1932,252)
 cost=read(J/'COST.json');assert Decimal(cost['unresolved_reserve_usd'])==0 and Decimal(cost['actual_usd'])<=10
 packet=ROOT/'cache/g_agreement/understand/e98/judge_packet_v2';inp=read(packet/'INPUT_SEAL.json');assert sha(packet/'INPUT_SEAL.json')==seal['input_sha256'];verify(packet,inp['files'])
 ids=set(read(packet/'NATIVE_IDS.json'));primary=read(J/'PRIMARY.json');old=read(J/'ORIGINAL.json');regex=read(J/'REGEX_RESOLVED.json');counts=read(J/'COUNT_MEASURES.json')
 groups=[{x['id'] for x in v} for v in [primary,regex,counts]];assert [len(x)for x in groups]==[1785,231,168] and set.union(*groups)==ids and sum(map(len,groups))==len(ids)==2184
 assert {x['id']for x in old}==set(read(packet/'ORIGINAL_IDS.PRIVATE.json')) and len(old)==447
 for name in ['REGEX_RESOLVED.json','COUNT_MEASURES.json']:assert read(J/name)==read(packet/name)
 ns=ROOT/'cache/g_agreement/understand/e98/reader_native_complete/out/OUTPUT_SEAL.json';assert sha(ns)==seal['native_seal_sha256'];native=read(ns);assert native['status']=='COMPLETE';verify(ns.parent,native['files'])
 assert {p.stem for p in(ns.parent/'records').glob('*.json')}==ids
 truncated=sum(bool(read(p)['truncated']) for p in(ns.parent/'records').glob('*.json'));assert truncated==74
 src=ROOT/'results/g_agreement/understand/blind_judge/e98_bank/SOURCE_SEAL.json';assert sha(src)==seal['source_seal_sha256'];verify(ROOT,read(src)['files'])
 responses=sorted((Q/'ledger').glob('E98_*_attempt*/*.response.json'));assert responses
 route=read(J/'ROUTE_AUDIT.json');assert route['routes'] and all(x['tag']=='google-vertex/global' and x['provider_name']=='Google' and x['model_id']=='google/gemini-3.1-flash-lite' for x in route['routes'])
 byhash={sha(p):p for p in responses};assert len(route['requests'])==len(responses)
 for x in route['requests']:
  assert x['provider']=='Google' and x['model'] in ('google/gemini-3.1-flash-lite','google/gemini-3.1-flash-lite-001') and x['response_sha256'] in byhash
 assert sum((Decimal(x['cost_usd']) for x in route['requests']),Decimal(0))==Decimal(cost['actual_usd'])
 proof=Q/'ledger/route/OPENROUTER_PRIVACY_PROOF.json';assert sha(proof)==route['privacy_proof_sha256']
 members={}
 for n in seal['files']:members['judgments/'+n]=J/n
 members['judgments/JUDGMENT_SEAL.json']=J/'JUDGMENT_SEAL.json';members['ledger/ledger.jsonl']=Q/'ledger/ledger.jsonl'
 for p in responses:members['raw/'+str(p.relative_to(Q/'ledger'))]=p
 for n in read(src)['files']:members['source/'+n]=ROOT/n
 members['source/SOURCE_SEAL.json']=src;members['code/closeout.py']=Path(__file__).resolve()
 # Fail before writing if credentials appear; only generated reply content/opaque IDs are published.
 pat=re.compile(rb'hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}')
 key=os.environ.get('OPENROUTER_API_KEY','').encode()
 for name,p in members.items():
  b=p.read_bytes();assert not pat.search(b),'credential-pattern audit required: '+name
  assert not key or key not in b,'credential present'
 PUB.mkdir(parents=True)
 for n,p in members.items():
  dest=PUB/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);assert sha(dest)==sha(p)
 earliest=min(responses,key=lambda p:p.stat().st_mtime_ns);now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 receipt=dict(status='VERIFIED_COMPLETE_E98_JUDGMENTS',at_utc=now,judgment_seal_sha256=sha(J/'JUDGMENT_SEAL.json'),input_sha256=seal['input_sha256'],native_seal_sha256=seal['native_seal_sha256'],source_seal_sha256=sha(src),all_member_hashes_verified=True,full_native_ids=2184,primary=1785,original=447,regex_resolved=231,count_items=168,native_truncated_retained=74,route_privacy_verified=seal['route_verified'],actual_usd=cost['actual_usd'],unresolved_usd='0',allocation_usd='10',released_unused_allocation_usd=str(Decimal(10)-Decimal(cost['actual_usd'])),physical_cost_already_in_original_ledger=True,new_physical_charge_usd='0',raw_responses=len(responses),first_judgment_output=dict(path=str(earliest),mtime_ns=earliest.stat().st_mtime_ns),scientific_analysis_run=False)
 dump(RECEIPT,receipt);dump(PUB/'CLOSEOUT.json',receipt)
 dump(PUB/'SEAL.json',dict(status='COMPLETE_TERMINAL_PUBLICATION_NO_ANALYSIS',at_utc=now,files={str(p.relative_to(PUB)):sha(p)for p in PUB.rglob('*')if p.is_file()}))
 event=dict(event='judge_bank_closed',bank='E98',at_utc=now,actual_usd=cost['actual_usd'],physical_cost_already_in_canonical_ledger=True,new_physical_charge_usd=0,released_unused_allocation_usd=receipt['released_unused_allocation_usd'],closeout_sha256=sha(RECEIPT))
 compute=ROOT/'results/g_agreement/compute.jsonl'
 lines=[json.loads(l)for l in compute.read_text().splitlines()if l.strip()];assert not any(x.get('event')=='judge_bank_closed'and x.get('bank')=='E98'for x in lines)
 with compute.open('a') as f:f.write(json.dumps(event,sort_keys=True)+'\n')
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
