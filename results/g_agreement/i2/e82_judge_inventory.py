"""CPU-only exact E82 grouped-position intake. No judge calls or paid admission.

Retain every source position per item and reader, source target aliases and the
10 missing-truth items. This inventory does not invent a grouped judge renderer.
"""
import json,hashlib,os
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,ensure_ascii=False);f.write('\n')
def build():
 os.umask(0o077);root=Path.cwd();h=root/'cache/g_agreement/i2/e82_judge_cpu_v1';assert not h.exists()
 run=root/'cache/g_agreement/i2/section212_restarts_v1/e82-full-a1';out=run/'terminal_pull/outputs';verification=read(run/'PULL_VERIFIED.json');seal=read(out/'OUTPUT_SEAL.json')
 assert verification['exact_registered_items_positions'] and verification['full_scientific_outputs']==13580
 assert sha(out/'OUTPUT_SEAL.json')==verification['output_seal_sha256']=='f9fd7603fccdadb2ed1c412801833e2d8979fe49a10a1695d3a88d4e6defa2fa'
 for name,digest in seal['files'].items():assert sha(out/name)==digest,name
 owner=root.parent/'wt-wtext/results/g_agreement/understand/e82';request=read(owner/'LAUNCH_REQUEST.json');targets=Path(request['cpu_targets_path']);assert sha(targets)==request['cpu_targets_sha256']=='9ff51079b6327439f67e5940ccf1382d34947d989ebc273807229ce8a8cc6652'
 public=read(run/'inputs/PUBLIC_INPUTS.json');metadata=read(targets);labels={x['id']:x for x in metadata};assert len(labels)==209 and set(labels)=={x['id'] for x in public}
 missing={x['id']for x in metadata if x['truth'] is None};assert len(missing)==10
 expected={x['id']:x['read_positions'] for x in public};groups=[];joins=[]
 for reader,layer in [('oracle',44),('nla',42)]:
  by={i:{}for i in expected}
  for f in sorted((out/'jobs').glob(reader+'_*.json')):
   for x in read(f):
    assert x['reader']==reader and x['layer']==layer and x['position'] in expected[x['unit_id']]
    assert x['position'] not in by[x['unit_id']];by[x['unit_id']][x['position']]=x['text']
  assert sum(map(len,by.values()))==6790
  for ident,positions in expected.items():
   assert set(by[ident])==set(positions)
   opaque=hashlib.sha256(('E82|'+reader+'|'+ident).encode()).hexdigest()[:32]
   groups.append(dict(id=opaque,positions=[dict(position=p,readout=by[ident][p])for p in positions]))
   joins.append(dict(labels[ident],id=opaque,reader=reader,source_public_id=ident,truth_contrast_eligible=ident not in missing))
 assert len(groups)==418 and len({x['id'] for x in groups})==418 and sum(len(x['positions'])for x in groups)==13580
 h.mkdir();write(h/'GROUPED_READOUTS.json',groups);write(h/'JOIN_MAP.PRIVATE.json',joins)
 write(h/'SOURCE_BINDINGS.PRIVATE.json',dict(output_seal_sha256=sha(out/'OUTPUT_SEAL.json'),owner_request_sha256=sha(owner/'LAUNCH_REQUEST.json'),targets_sha256=sha(targets),public_inputs_sha256=sha(run/'inputs/PUBLIC_INPUTS.json'),owner_request=str(owner/'LAUNCH_REQUEST.json'),targets=str(targets)))
 receipt=dict(at_utc=datetime.now(timezone.utc).isoformat(),experiment='E82',status='EXACT_GROUPED_CPU_INVENTORY_RENDERER_AND_WIRE_PREFLIGHT_PENDING',source_items=209,reader_item_groups=418,read_positions=6790,native_outputs=13580,truth_contrast_items=199,belief_only_no_canonical_truth_items=10,families=dict(Counter(x['family']for x in metadata)),all_positions_grouped_by_item=True,output_seal_sha256=sha(out/'OUTPUT_SEAL.json'),private_target_sha256=sha(targets),inventory_sha256=sha(h/'GROUPED_READOUTS.json'),private_join_sha256=sha(h/'JOIN_MAP.PRIVATE.json'),bank_cap_usd=3,full_wire_cost_known=False,judge_calls=0,reservations_usd=0,scientific_verdict_claimed=False,next_action='Bind the exact registered grouped-position renderer with separate belief/truth judgments and seeded original-rubric comparison, preserving all positions and missing-truth belief-only reporting. Then full exact-wire cap/global/privacy preflight; no sends or allocation from inventory alone.')
 write(h/'INVENTORY_RECEIPT.json',receipt);write(root/'results/g_agreement/i2/E82_JUDGE_CPU_INVENTORY.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':build()
