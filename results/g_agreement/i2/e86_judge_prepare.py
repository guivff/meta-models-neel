"""CPU-only E86 exact released-test packet; no API, reservation or scientific score.

Truth/lie A/B order is the registered E86 channel convention. Original question
text defines the property; original selected truth/opposite answer are verbatim.
No source filtering, selection, probes or reader stages are rerun.
"""
from pathlib import Path
from collections import Counter
import json,hashlib,sys,datetime,os

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
def build():
 os.umask(0o077);r=Path.cwd();h=r/'cache/g_agreement/i2/e86_judge_cpu_v1';assert not h.exists()
 run=r/'cache/g_agreement/i2/section212_restarts_v1/e86-a2';selected=r/'cache/g_agreement/i2/e86_selected_once';release=run/'READER_RELEASE.json';pull=run/'full_terminal_pull/full_outputs';seal=read(pull/'OUTPUT_SEAL.json');verify=read(run/'FULL_PULL_VERIFIED.json')
 assert sha(pull/'OUTPUT_SEAL.json')==verify['output_seal_sha256']=='cfa46523e1fe50337113679fbdada86568a0e6e92348088e28f5a978175fa075'
 assert seal['status']=='COMPLETE' and seal.get('synthetic',False) is False
 for name,digest in seal['files'].items():assert sha(pull/name)==digest,name
 assert sha(release)=='a13b247655ff2d65d69933c6bb20b3b3b67a933232a6adcdf0f864ea0097f38a'
 selection_seal=read(selected/'SELECTION_SEAL.json')
 for name,digest in selection_seal['files'].items():assert sha(selected/name)==digest,name
 allowed=set(read(release)['released_ids']);assert len(allowed)==400
 labels={x['capture_public_id']:x for x in read(selected/'SELECTED.PRIVATE.json')}
 keep={i:labels[i] for i in allowed};assert Counter((x['subset'],x['arm'],x['split']) for x in keep.values())=={('yn','honest','test'):200,('yn','role','test'):200}
 records=[]
 for reader,layer in [('oracle',44),('nla',42)]:
  rs=[]
  for p in sorted((pull/'jobs').glob(reader+'_*.json')):rs.extend(read(p))
  assert len(rs)==400 and {x['unit_id'] for x in rs}==allowed and len({x['id'] for x in rs})==400
  assert all(x['reader']==reader and x['layer']==layer for x in rs)
  records.extend(rs)
 packet=[];joins=[]
 for x in records:
  meta=keep[x['unit_id']];truth=meta['truth'];wrong=meta['distractor']
  assert {truth,wrong}=={'Yes','No'} and meta['eligible_arms']['honest']==truth
  if meta['arm']=='role':assert meta['lie_word']==wrong and meta['eligible_arms']['role']==wrong
  ident=hashlib.sha256(('E86|'+x['reader']+'|'+x['id']).encode()).hexdigest()[:32]
  packet.append(dict(id=ident,property=meta['questions'][0],values=dict(A=truth,B=wrong),readout=x['text']))
  joins.append(dict(id=ident,source_id=meta['id'],capture_public_id=x['unit_id'],position=x['position'],reader=x['reader'],arm=meta['arm'],subset=meta['subset'],split='test',correct_value='A',truth=truth,wrong=wrong))
 assert len(packet)==800 and len({x['id'] for x in packet})==800
 h.mkdir();write(h/'JUDGE_PACKET.json',packet);write(h/'JOIN_MAP.PRIVATE.json',joins)
 pub=r/'cache/g_agreement/i2/publication';sys.path.insert(0,str(pub))
 from projects.g_agreement.understand.blind_judge import run as route_run,later_runner,channels81_86,rubric202
 from projects.g_agreement.understand.blind_judge.judgment_adapter402 import render_record
 from projects.g_agreement.understand.blind_judge.privacy79 import redact
 from decimal import Decimal
 rubric=channels81_86.rubric_path('E86');(h/'JUDGE_RUBRIC.txt').write_bytes(rubric.read_bytes());original_ids=rubric202.original_ids([x['id'] for x in packet],'E86');assert len(original_ids)==200;write(h/'ORIGINAL_IDS.json',original_ids)
 write(h/'SOURCE_SEAL.json',dict(experiment='E86',complete=True,n=800,rubric_sha256=sha(h/'JUDGE_RUBRIC.txt'),value_order='truth_then_lie',behaviour_gate_verified=True,files={n:sha(h/n) for n in ['JUDGE_PACKET.json','JUDGE_RUBRIC.txt','ORIGINAL_IDS.json']},scientific_output_seal_sha256=sha(pull/'OUTPUT_SEAL.json'),release_sha256=sha(release),selection_seal_sha256=sha(selected/'SELECTION_SEAL.json')))
 spec=dict(bank='E86',source_seal=str(h/'SOURCE_SEAL.json'),source_seal_sha256=sha(h/'SOURCE_SEAL.json'),source_packet=str(h/'JUDGE_PACKET.json'),rubric=str(h/'JUDGE_RUBRIC.txt'));channels81_86.convert(spec,h/'converted_packet')
 text=rubric.read_text();rendered=[render_record(x,text) for x in packet];rendered,audit=redact(rendered,'E86',addresses=True);old=rubric202.BASE.read_text();wanted=set(original_ids);original=[dict(x,rubric=x['rubric'].replace(text,old,1)) for x in rendered if x['id'] in wanted]
 route=read(pub/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json');api,privacy,protocol,io=route_run.route_modules(route);components=[];wires=[]
 for xs,rr in [(rendered,text),(original,old)]:
  ws=[later_runner.channel_payload(xs[i:i+4],rr,'E56',protocol) for i in range(0,len(xs),4)];wires.extend(sha256(io.canonical(w).encode()) for w in ws);components.append(dict(records=len(xs),requests=len(ws),first_pass_upper_usd=str(sum((api.upper(w) for w in ws),Decimal(0)))))
 total=sum((Decimal(x['first_pass_upper_usd']) for x in components),Decimal(0));proof=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='CPU_FULL_SCOPE_PREFLIGHT_FITS_BANK_CAP_PENDING_GLOBAL_PRIVACY_ALLOCATION' if total<=3 else 'CPU_FULL_SCOPE_NO_FIT_REGISTERED_BANK_CAP',bank='E86',cap_usd=3,first_pass_upper_usd=str(total),components=components,primary_records=800,original_rubric_records=200,total_requests=len(wires),source_seal_sha256=sha(h/'SOURCE_SEAL.json'),packet_seal_sha256=sha(h/'converted_packet/PACKET_SEAL.json'),private_join_sha256=sha(h/'JOIN_MAP.PRIVATE.json'),redaction_audit_sha256=sha256(json.dumps(audit,sort_keys=True).encode()),wire_hashes_sha256=sha256(json.dumps(wires).encode()),source_questions_and_truth_wrong_verbatim=True,truth_labels_private_cpu_only=True,gate_scope='400 released honest+role test items only; lie BOW FAIL and open underpowered preserved',judge_calls=0,reservations_usd=0,scope_rules_route_output_limits_unchanged=True,pending=['Fresh separate global500 actual+held reconciliation without full-programme doublecount','Live pinned route/privacy/credit checks','Posted bank allocation before dispatch','Exact destination authorization if required by actual approval review'])
 write(h/'CPU_PREFLIGHT.json',proof);write(r/'results/g_agreement/i2/E86_FULL_JUDGE_CPU_PREFLIGHT.json',proof);print(json.dumps(proof))
def sha256(data):return hashlib.sha256(data).hexdigest()
if __name__=='__main__':build()
