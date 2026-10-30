"""CPU-only E99 exact three-family call inventory and initial-stage wire costs.

No judging, allocation, scientific scoring or reduction of the frozen grid.
Dependent hallucination verify/corroboration stages remain explicit DAG nodes;
their exact wires require prior KEPT outputs and fresh whole-bank admission.
"""
import json,hashlib,sys,os,datetime
from pathlib import Path
from collections import Counter
from decimal import Decimal

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(v.encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,ensure_ascii=False);f.write('\n')
def main():
 os.umask(0o077);r=Path.cwd();h=r/'cache/g_agreement/i2/e99_judge_cpu_v1';assert not h.exists();pub=r/'cache/g_agreement/i2/publication';sys.path.insert(0,str(pub))
 from projects.g_agreement.understand.blind_judge.e99_families import Renderers
 from projects.g_agreement.understand.blind_judge.e99_channel import frozen_wire
 from projects.g_agreement.understand.blind_judge import run
 renderer=Renderers();sidecar=renderer.sidecar('shared_private_items');source={x['id']:x for x in sidecar}
 master=r/'cache/g_agreement/i2/e99_core_three_production_v1/operator0-a1/inputs/items.json';assert sha(master)=='bffd1667091b19ac8e3b84f7ac00d7253365bdee6993f0732a6ca78af2492a4f';inputs=read(master);assert len(inputs)==349
 selected={x['id']:x for x in inputs};assert set(selected)<=set(source)
 assert Counter(x['family'] for x in inputs)==Counter({x['family']:sum(y['family']==x['family'] for y in inputs) for x in inputs})
 by_family={}
 for family in ('user_modeling','directed_modulation'):
  items=[dict(source[x['id']]['source_item'],id=x['id']) for x in inputs if x['family']==family]
  by_family[family]=renderer.mc99.options(family,items)
 route=read(pub/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json');api,privacy,protocol,io=run.route_modules(route)
 records=[];seals=[];files={}
 for shard in range(4):
  root=r/f'cache/g_agreement/i2/e99_core_three_production_v1/operator{shard}-a1/terminal_pull/outputs';s=read(root/'OUTPUT_SEAL.json');assert s['status']=='COMPLETE' and not s.get('synthetic',False)
  for name,value in s['files'].items():assert sha(root/name)==value,name
  seals.append(sha(root/'OUTPUT_SEAL.json'))
  for p in sorted((root/'jobs').glob('*.json')):
   files[str(p)]=sha(p);records.extend(read(p))
 assert len(records)==26060 and len({x['id'] for x in records})==26060
 assert Counter(x['family'] for x in records)==dict(hallucination=6680,user_modeling=13825,directed_modulation=5555)
 assert Counter(x['arm'] for x in records)==dict(real=20415,placebo=5645)
 nla_index={(x['unit_id'],x['position']):x for x in records if x['reader']=='nla'};assert len(nla_index)==sum(x['reader']=='nla' for x in records)
 allrows={x['id']:x for x in records};dag=[];grid=[];totals=Counter();request_hashes={};initial=Decimal(0)
 call=lambda ident,stage:digest('E99|'+ident+'|'+stage)[:32]
 for x in records:
  fam=x['family'];paired=x['paired_capture_id'];assert paired in selected and x['family']==source[paired]['family']
  item=source[paired]['source_item'];expected=selected[paired];assert x['position'] in expected['positions'] or x.get('single_site')
  if fam=='hallucination':
   sites={s['pos']:s for s in item['sites']};assert x['position'] in sites
   stage='audit';rendered=renderer.render(fam,stage,item=item,site=sites[x['position']],readout=x['text'])
  else:
   stage='identify';rendered=renderer.render(fam,stage,item=item,readout=x['text'],options=by_family[fam][paired]['options'])
  wire=frozen_wire(rendered,protocol);upper=api.upper(wire);initial+=upper;totals[fam]+=upper
  ident=call(x['id'],stage);wire_hash=digest(io.canonical(wire));request_hashes[ident]=wire_hash
  dag.append(dict(id=ident,family=fam,channel='family',stage=stage,depends_on=[]))
  required=[ident]
  if fam=='hallucination':
   verify=call(x['id'],'verify');dag.append(dict(id=verify,family=fam,channel='family',stage='verify',depends_on=[ident]));required.append(verify)
   if x['reader']=='oracle' and x['layer']==44:
    assert (x['unit_id'],x['position']) in nla_index
    corroboration=call(x['id'],'corroboration');dag.append(dict(id=corroboration,family=fam,channel='corroboration',stage='corroboration',depends_on=[verify]));required.append(corroboration)
  grid.append(dict(id=x['id'],family=fam,channel='family',arm=x['arm'],required_call_ids=required))
 assert len({x['id'] for x in dag})==len(dag)
 h.mkdir();write(h/'CALL_DAG.PRIVATE.json',dict(cells=grid,calls=dag));write(h/'WIRE_HASHES.PRIVATE.json',request_hashes)
 write(h/'SOURCE_BINDINGS.PRIVATE.json',dict(job_files=files,output_seal_sha256=seals,source_items_sha256=renderer.dependencies['shared_private_items']['sha256'],master_items_sha256=sha(r/'cache/g_agreement/i2/e99_core_three_production_v1/operator0-a1/inputs/items.json')))
 proof=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='CPU_INITIAL_STAGE_NO_FIT_BANK40_DEPENDENT_WIRES_NOT_YET_AVAILABLE' if initial>40 else 'CPU_INITIAL_STAGE_PREFLIGHT_DEPENDENT_WIRES_PENDING',bank='E99',registered_cap_usd=40,initial_stage_upper_usd=str(initial),initial_by_family={k:str(v) for k,v in totals.items()},initial_calls=len(records),dependent_calls=len(dag)-len(records),all_DAG_calls=len(dag),cells=26060,real_cells=20415,placebo_cells=5645,stage_counts=dict(Counter(x['stage'] for x in dag)),whole_grid_frozen_no_sampling=True,source_output_seals=seals,call_DAG_sha256=sha(h/'CALL_DAG.PRIVATE.json'),wire_hashes_sha256=sha(h/'WIRE_HASHES.PRIVATE.json'),source_bindings_sha256=sha(h/'SOURCE_BINDINGS.PRIVATE.json'),judge_calls=0,reservations_usd=0,scope_reduction_step=0,complete_cost_admission=False,pending='Full dependent-stage bound and unchanged scope/per-bank cost decision before allocation or calls; never use initial-only figure as whole-run cost.')
 write(h/'INITIAL_STAGE_PREFLIGHT.json',proof);write(r/'results/g_agreement/i2/E99_JUDGE_INITIAL_STAGE_CPU_PREFLIGHT.json',proof);print(json.dumps(proof))
if __name__=='__main__':main()
