"""CPU-only E82 grouped §172/§202 renderer and exact first-pass cost.

All positions stay in each item/reader group. Belief and truth receive separate
opaque judgment records; candidate order is fixed independently of either target.
Absent truth produces no truth record and no fabricated opposing candidate.
No API client, reservation, scoring, or scientific analysis runs here.
"""
import hashlib,json,sys,os
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone

def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(p.read_bytes())
def read(p):return json.loads(p.read_text())
def write(p,x):
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def candidates(meta):
 belief=list(dict.fromkeys(meta['belief']+meta['belief_aliases']))
 truth=list(dict.fromkeys((meta['truth'] or [])+meta['truth_aliases']))
 assert belief and all(type(x)is str and x for x in belief+truth)
 if not truth:return {'A':belief,'B':[]},{'belief':'A'}
 # Candidate order is a frozen opaque group-ID hash, independent of label/value.
 order=digest(('20261028:E82:candidates:'+meta['id']).encode())
 values={'A':belief,'B':truth} if int(order,16)%2==0 else {'A':truth,'B':belief}
 return values,{'belief':'A' if values['A']==belief else 'B','truth':'A' if values['A']==truth else 'B'}
def make_records(groups,joins,render,rubric):
 by={x['id']:x for x in joins};assert len(by)==len(groups)
 records=[];private=[]
 for group in groups:
  m=by[group['id']];values,targets=candidates(m)
  assert bool(m['truth'])==m['truth_contrast_eligible']
  for target,letter in targets.items():
   ident=digest(('E82:separate:'+target+':'+group['id']).encode())[:32]
   base=render(dict(id=ident,property=m['target_kind'],values=values,readout=''),rubric)
   records.append(dict(id=ident,rubric=base['rubric'],positions=[dict(p)for p in group['positions']]))
   private.append(dict(id=ident,group_id=group['id'],target=target,target_letter=letter,allowed_values=['A','B']if m['truth'] else ['A'],source_public_id=m['source_public_id'],reader=m['reader'],family=m['family']))
 assert len({x['id']for x in records})==len(records)
 return records,private

def wire(records,rubric,protocol,payload):
 # Exactly the E56 route, token limit and category/value schema. Group metadata is
 # outside native text; no first-position rule, position selection or text merge.
 body=payload([],rubric,'E56',protocol)
 assert all(set(x)=={'id','rubric','positions'} for x in records)
 body['messages'][1]['content']=json.dumps(records,ensure_ascii=False)
 return body

def validate_code(group,code,allowed_values,validator):
 assert set(code)=={'id','category','values','evidence'} and code['id']==group['id']
 assert set(code['values'])<=set(allowed_values),'NO_UNDEFINED_MISSING_TRUTH_VALUE'
 # Standard category/value rules validate on the union, but evidence must be
 # wholly within one original native readout, never a header or cross-boundary.
 text='\n'.join(p['readout']for p in group['positions'])
 validator([dict(id=group['id'],readout=text)],[code],'E56')
 evidence=code['evidence']
 assert code['category']=='silent' or any(evidence in p['readout']for p in group['positions'])

def main():
 os.umask(0o077);root=Path.cwd();home=root/'cache/g_agreement/i2/e82_judge_cpu_v1';out=home/'grouped_adapter_v1';assert not out.exists()
 receipt=read(home/'INVENTORY_RECEIPT.json');assert sha(home/'GROUPED_READOUTS.json')==receipt['inventory_sha256'] and sha(home/'JOIN_MAP.PRIVATE.json')==receipt['private_join_sha256']
 pub=root/'cache/g_agreement/i2/publication';sys.path.insert(0,str(pub))
 from projects.g_agreement.understand.blind_judge import run,rubric202,channels81_86
 from projects.g_agreement.understand.blind_judge.judgment_adapter402 import render_record
 from projects.g_agreement.understand.blind_judge.privacy79 import redact
 rubric=channels81_86.rubric_path('E82').read_text();old=rubric202.BASE.read_text()
 groups=read(home/'GROUPED_READOUTS.json');joins=read(home/'JOIN_MAP.PRIVATE.json')
 records,private=make_records(groups,joins,render_record,rubric)
 assert len(records)==816 and sum(x['target']=='belief'for x in private)==418 and sum(x['target']=='truth'for x in private)==398
 assert sum(len(x['positions'])for x in groups)==13580
 # Fixed redaction policy is applied to every original position, before wires.
 flat=[dict(id=x['id']+':'+str(p['position']),readout=p['readout'])for x in records for p in x['positions']]
 redacted,audit=redact(flat,'E82',addresses=True);it=iter(redacted)
 for group in records:
  group['positions']=[dict(p,readout=next(it)['readout'])for p in group['positions']]
 assert next(it,None)is None
 original_ids=rubric202.original_ids([x['id']for x in records],'E82');assert len(original_ids)==204
 chosen=set(original_ids);original=[dict(x,rubric=x['rubric'].replace(rubric,old,1))for x in records if x['id']in chosen]
 route=read(pub/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json');api,privacy,protocol,io=run.route_modules(route)
 assert protocol.MODEL=='google/gemini-3.1-flash-lite' and protocol.PROVIDER=='google-vertex/global'
 components=[];hashes=[]
 for label,items,rr in [('primary',records,rubric),('original',original,old)]:
  wires=[wire([x],rr,protocol,run.payload)for x in items]
  assert all(w['max_tokens']==4096 for w in wires)
  components.append(dict(channel=label,records=len(items),requests=len(wires),upper_usd=str(sum((api.upper(w)for w in wires),Decimal(0))),max_wire_bytes=max(len(io.canonical(w).encode())for w in wires)))
  hashes.extend(digest(io.canonical(w).encode())for w in wires)
 total=sum((Decimal(x['upper_usd'])for x in components),Decimal(0));out.mkdir()
 write(out/'GROUPED_PACKET.json',records);write(out/'TARGET_MAP.PRIVATE.json',private);write(out/'ORIGINAL_IDS.json',original_ids);write(out/'WIRE_HASHES.json',hashes)
 proof=dict(at_utc=datetime.now(timezone.utc).isoformat(),bank='E82',status='FULL_SCOPE_CPU_PREFLIGHT_NO_FIT_BANK3'if total>3 else 'FULL_SCOPE_CPU_PREFLIGHT_FITS_PENDING_ADMISSION',first_pass_upper_usd=str(total),registered_cap_usd=3,primary_records=816,belief_records=418,truth_records=398,original_rubric_records=204,total_requests=len(hashes),source_groups=418,native_outputs=13580,all_positions_retained=True,truth_missing_items=10,no_truth_judgment_or_distractor_invented=True,missing_truth_B_description_empty=True,candidate_order_label_independent=True,separate_target_records=True,components=components,redaction_audit=audit,renderer_code_sha256=sha(Path(__file__)),source_inventory_sha256=sha(home/'INVENTORY_RECEIPT.json'),rubric_sha256=digest(rubric.encode()),original_rubric_sha256=digest(old.encode()),route_seal_sha256=sha(pub/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'),files={p.name:sha(p)for p in out.iterdir()},judge_calls=0,reservations_usd=0,pending=['Bank cap fit or actual human ruling','Fresh global actual/open ledger, live route/privacy/credits','Posted allocation before dispatch'])
 write(out/'PREFLIGHT.json',proof);write(root/'results/g_agreement/i2/E82_FULL_JUDGE_CPU_PREFLIGHT.json',proof);print(json.dumps(proof))
if __name__=='__main__':main()
