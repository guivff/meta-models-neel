"""Freeze CPU-only E107 design/availability/target maps; no outcomes or paid calls."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,shutil,datetime,os
r=Path.cwd();h=r/'cache/g_agreement/i2/e107_cpu_inventory_v1';read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();roster=read(h/'CANDIDATE_ROSTER.PRIVATE.json');prefix=read(h/'GENERATION_SOURCE_BINDINGS.PRIVATE.json');assert {x['id']for x in roster}=={x['id']for x in prefix}
e81path=r/'cache/g_agreement/i2/e81_judge_cpu_v3/JOIN_MAP.PRIVATE.json';e82path=r/'cache/g_agreement/i2/e82_judge_cpu_v1/JOIN_MAP.PRIVATE.json';e86path=r/'cache/g_agreement/i2/e86_judge_cpu_v1/JOIN_MAP.PRIVATE.json';targetpath=r/'cache/g_agreement/i2/e82_judge_cpu_v1/grouped_adapter_v1/TARGET_MAP.PRIVATE.json'
indices={b:{x['id']:x for x in read(p)}for b,p in [('E81',e81path),('E82',e82path),('E86',e86path)]};letters={}
for x in read(targetpath):letters[(x['source_public_id'],x['reader'],x['target'])]=x['target_letter']
e73keys={};keypaths=[]
for name,sub in [('e73_judge_start_candidate','prepared'),('e73_controls_judging_candidate','')]:
 p=r/'cache/g_agreement/i2'/name/sub/'private/JOIN_MAP.json';keypaths.append(p)
 for x in read(p):
  if x['reader']=='oracle':e73keys[x['source_id']]=x
inventory=[];maps=[];counts=Counter();code_unavailable=0
for m in roster:
 bank=m['bank'];joined=[indices[bank][ident]for ident in m['source_records']];meta={k:m[k]for k in ['id','bank','row','item_id']};systems=['oracle','nla','outside'];unavailable={};by={};lineage={}
 if bank=='E81':
  j=next(x for x in joined if x['arm']=='generic');label=j['label'];assert label in [0,1]
  if j['bank']=='e73':
   k=e73keys[j['source_id']];assert k['label']==label and k['state']==j['row'] and k['value']==('B'if label else'A');letter=k['value']
  else:letter='A'if label else'B'
  systems+=['qwen_self']
  if j['bank']=='e49':
   systems=['outside','qwen_self'];unavailable={s:'original categorical code unavailable; native text present; original metric is statements49 regex'for s in ['oracle','nla']};code_unavailable+=1
  by={s:{'S':letter}for s in systems};lineage=dict(original_E81_generic_id=j['id'],original_E81_join_sha256=sha(e81path),original_label_mapping='E73 0=A/1=B; E49/E57/E59 1=A/0=B; exact native candidate orders checked',native_text_availability_sha256=sha(h/'E81_NATIVE_AVAILABILITY_v2.PRIVATE.json'))
 elif bank=='E82':
  j=joined[0];assert len(joined)==2 and {x['reader']for x in joined}=={'oracle','nla'};has_truth=j['truth_contrast_eligible'];meta['cohort']='belief_wrong'if has_truth else'no_canonical_truth';counts['E82/'+meta['cohort']]+=1
  targets=['belief','truth']if has_truth else['belief']
  for s in ['oracle','nla']:by[s]={t:letters[(j['source_public_id'],s,t)]for t in targets}
  outside_belief=('A'if hashlib.sha256(('E107|outside|'+m['id']).encode()).digest()[0]%2==0 else'B')if has_truth else'A';by['outside']={'belief':outside_belief}
  if has_truth:by['outside']['truth']='B'if outside_belief=='A'else'A'
  lineage=dict(original_source_public_id=j['source_public_id'],original_E82_target_map_sha256=sha(targetpath),outside_order_policy='sha256(E107|outside|inventoryID) first-byte parity; A-only when canonical truth absent',source_belief=j['belief'],source_truth=j['truth'],source_belief_aliases=j['belief_aliases'],source_truth_aliases=j['truth_aliases'])
 else:
  assert {x['reader']for x in joined}=={'oracle','nla'}and len(joined)==2 and all(x['split']=='test'and x['arm']in ['honest','role']and x['subset']=='yn'for x in joined);by={s:{'truth':'A'}for s in systems};lineage=dict(original_capture_public_id=joined[0]['capture_public_id'],original_E86_join_sha256=sha(e86path),original_fixed_order='truth=A/wrong=B',source_truth=joined[0]['truth'],source_wrong=joined[0]['wrong'])
 meta.update(systems=systems,unavailable_systems=unavailable,target_letters_by_system=by);inventory.append(meta);maps.append(dict(id=m['id'],target_letters_by_system=by,source_lineage=lineage));counts[bank]+=1
assert counts['E81']==3688 and counts['E82']==209 and counts['E86']==400 and counts['E82/belief_wrong']==199 and counts['E82/no_canonical_truth']==10 and code_unavailable==1176
rows={b:sorted({x['row']for x in inventory if x['bank']==b})for b in ['E81','E82','E86']};assert len(rows['E81'])==37
out=r/'results/g_agreement/i2/e107_inventory_v1';assert not out.exists(),'preserve original frozen inventory; no replay';out.mkdir();os.chmod(out,0o700)
(out/'.gitignore').write_text('/INVENTORY.json\n/TARGET_MAPS.PRIVATE.json\n/GENERATION_SOURCE_BINDINGS.PRIVATE.json\n')
for name,data in [('INVENTORY.json',inventory),('TARGET_MAPS.PRIVATE.json',maps),('GENERATION_SOURCE_BINDINGS.PRIVATE.json',prefix)]:
 (out/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n');(out/name).chmod(0o600)
provenance=dict(experiment='E107',status='DESIGN_FROZEN_BEFORE_ANY_E107_OUTPUT_NO_ADMISSION',source_join_sha256={b:sha(p)for b,p in [('E81',e81path),('E82',e82path),('E86',e86path)]},original_E82_target_map_sha256=sha(targetpath),original_E73_key_sha256=[sha(p)for p in keypaths],native_availability_sha256=sha(h/'E81_NATIVE_AVAILABILITY_v2.PRIVATE.json'),candidate_generation_sha256=sha(h/'GENERATION_CANDIDATE.json'),analysis_adapter_commit='280974179e094186d2f78ac6482dfb0f2c6aebe7',all37_E81_rows_retained=True,E49_unavailable_native_code_items=1176,E49_native_text_present=True,per_system_target_order_preserved=True,original_codes_and_seals_unmodified=True,registered_cap_usd=15,generation_calls=0,judge_calls=0,analysis_invoked=False,privacy_blocks_pending=5)
(out/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
seal=dict(experiment='E107',status='PRE_OUTPUT_DESIGN_INVENTORY_FROZEN',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files={n:sha(out/n)for n in ['INVENTORY.json','TARGET_MAPS.PRIVATE.json','GENERATION_SOURCE_BINDINGS.PRIVATE.json','PROVENANCE.json']},e81_rows=rows['E81'],surviving_e82_rows=rows['E82'],surviving_e86_rows=rows['E86'],counts=dict(counts),belief_right_source_cohort_absent=True,private_files_gitignored_and_not_for_publication=True,generation_calls=0,judge_calls=0,analysis_invoked=False)
(out/'INVENTORY_SEAL.json').write_text(json.dumps(seal,indent=2)+'\n');print(json.dumps(dict(inventory_seal_sha256=sha(out/'INVENTORY_SEAL.json'),items=len(inventory),rows={b:len(v)for b,v in rows.items()},private_payloads_excluded=True,no_admission=True)))
