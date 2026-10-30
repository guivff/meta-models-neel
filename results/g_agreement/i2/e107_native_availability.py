from pathlib import Path
from collections import Counter
import json,hashlib,datetime
r=Path.cwd();h=r/'cache/g_agreement/i2/e107_cpu_inventory_v1';mech=r.parent/'wt-wmech';read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();roster=read(h/'CANDIDATE_ROSTER.PRIVATE.json');native={};sourcehashes={}
def add(bank,source_id,reader,path,kind,locator):
 key=(bank,source_id,reader);entry=dict(path=str(path),kind=kind,locator=locator)
 if key in native:assert native[key]==entry,'DUPLICATE_NATIVE_SOURCE'
 native[key]=entry
 if str(path)not in sourcehashes:sourcehashes[str(path)]=sha(path)
for row in sorted({x['row'].split('/',1)[1]for x in roster if x['bank']=='E81' and x['row'].startswith('e49/')}):
 for reader in ['oracle','nla']:
  p=mech/'cache/g_agreement/understand/e49/verified_section149/out/readers'/row/(reader+'_native.jsonl')
  if not p.exists():continue
  for i,line in enumerate(p.read_text().splitlines()):add('e49',json.loads(line)['id'],reader,p,'native_jsonl',dict(line=i,text_key='text'))
for bank,base,keyfile in [
 ('e57',mech/'cache/g_agreement/understand/e56_e57/verified_pull_single_v1/e57','JUDGE_KEY.PRIVATE.json'),
 ('e59',mech/'cache/g_agreement/understand/analysis5968_verified/E59','PRIVATE_KEY.json')]:
 kp=base/keyfile;pp=base/'blind/JUDGE_PACKET.json';sourcehashes[str(kp)]=sha(kp);packet={x['id']:i for i,x in enumerate(read(pp))}
 for x in read(kp):
  unit,reader,repeat=x['source_id'].rsplit(':',2)
  if reader not in ['oracle','nla']or repeat!='0':continue
  assert x['opaque_id']in packet
  add(bank,unit,reader,pp,'frozen_blind_packet',dict(index=packet[x['opaque_id']],text_key='readout',opaque_id=x['opaque_id']))
for name in ['e73_judge_start_candidate','e73_controls_judging_candidate']:
 p=r/'cache/g_agreement/i2'/name/('prepared/private/JOIN_MAP.json'if name=='e73_judge_start_candidate'else'private/JOIN_MAP.json');sourcehashes[str(p)]=sha(p)
 pp=r/'cache/g_agreement/i2'/name/('prepared/packet/JUDGE_PACKET.json'if name=='e73_judge_start_candidate'else'packet/JUDGE_PACKET.json');packet=read(pp);positions={x['id']:i for i,x in enumerate(packet)}
 for i,x in enumerate(read(p)):
  if x['reader']in ['oracle','nla']:
   assert x['opaque_id']in positions and isinstance(packet[positions[x['opaque_id']]]['readout'],str)
   add('e73',x['source_id'],x['reader'],pp,'original_native_packet',dict(index=positions[x['opaque_id']],opaque_id=x['opaque_id'],text_key='readout'))
metadata=[];counts=Counter();missing=[]
for x in roster:
 if x['bank']!='E81':continue
 bank=x['row'].split('/',1)[0];entry=dict(id=x['id'],source_item_id=x['item_id'],row=x['row'],native_text_sources={})
 for reader in ['oracle','nla']:
  key=(bank,x['item_id'],reader)
  if key in native:entry['native_text_sources'][reader]=native[key];counts[bank+'/'+reader]+=1
  else:missing.append(dict(id=x['id'],row=x['row'],reader=reader))
 metadata.append(entry)
p=h/'E81_NATIVE_AVAILABILITY_v2.PRIVATE.json';payload=json.dumps(metadata,indent=2)+'\n'
if p.exists():assert p.read_text()==payload
else:p.write_text(payload);p.chmod(0o600)
proof=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),experiment='E107',state='CPU_SOURCE_TEXT_AVAILABILITY_AUDIT_NOT_FINAL_CODE_BINDING',E81_source_items=3688,native_text_source_counts=dict(counts),unmatched_native_text_sources=len(missing),native_availability_private_sha256=sha(p),source_file_hashes=sourcehashes,missing_not_zero=True,no_unmatched_items_dropped=True,original_code_and_target_binding_still_pending=True,generation_calls=0,judge_calls=0,analysis_invoked=False)
(r/'results/g_agreement/i2/E107_NATIVE_AVAILABILITY_AUDIT.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items()if k!='source_file_hashes'}))
