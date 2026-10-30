from pathlib import Path
import json,hashlib,os,datetime
r=Path.cwd();h=r/'cache/g_agreement/i2/e107_cpu_inventory_v1';read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();generic='Describe what is going on in this text and what comes next.'
roster=read(h/'CANDIDATE_ROSTER.PRIVATE.json');sources={
 'E81':r/'cache/g_agreement/i2/e81_serial_production_v1/shard0/inputs/PUBLIC_INPUTS.json',
 'E82':r/'cache/g_agreement/i2/section212_restarts_v1/e82-full-a1/inputs/PUBLIC_INPUTS.json',
 'E86':r/'cache/g_agreement/i2/section212_restarts_v1/e86-a2/inputs/PUBLIC_INPUTS.json'}
public={b:{x['id']:x for x in read(p)}for b,p in sources.items()};joins={b:read(r/('cache/g_agreement/i2/'+b.lower()+'_judge_cpu_v'+('3'if b=='E81'else'1')+'/JOIN_MAP.PRIVATE.json'))for b in sources}
source_hashes={b:sha(p)for b,p in sources.items()};index={b:{x['id']:x for x in xs}for b,xs in joins.items()};packet=[];binding=[]
for meta in roster:
 bank=meta['bank'];matched=[index[bank][i]for i in meta['source_records']]
 if bank=='E81':
  j=next(x for x in matched if x['arm']=='generic');public_id=j['id'];record=public[bank][public_id];assert record['prompt'].endswith('\n'+generic);prefix=record['prompt'][:-len('\n'+generic)];prompt=record['prompt'];assert record['read_position']==len(record['input_ids'])-1
 else:
  j=matched[0];public_id=j['source_public_id']if bank=='E82'else j['capture_public_id'];assert len({x.get('source_public_id',x.get('capture_public_id'))for x in matched})==1
  record=public[bank][public_id];prefix=record['prompt'];prompt=prefix+'\n'+generic
  if bank=='E82':assert max(record['read_positions'])==len(record['input_ids'])-1
  else:assert record['read_position']==len(record['input_ids'])-1
 assert prefix and prompt
 packet.append(dict(id=meta['id'],prompt=prompt))
 binding.append(dict(id=meta['id'],bank=bank,row=meta['row'],item_id=meta['item_id'],source_public_id=public_id,source_public_file=str(sources[bank]),source_public_file_sha256=source_hashes[bank],source_prompt_sha256=hashlib.sha256(prefix.encode()).hexdigest(),generation_prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),instruction=generic))
assert len(packet)==len({x['id']for x in packet})==4297
for name,data in [('GENERATION_CANDIDATE.json',packet),('GENERATION_SOURCE_BINDINGS.PRIVATE.json',binding)]:
 p=h/name;text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
 if p.exists():assert p.read_text()==text
 else:p.write_text(text);p.chmod(0o600)
proof=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),experiment='E107',state='CPU_EXACT_SOURCE_PREFIX_CANDIDATE_NO_DISPATCH',items=len(packet),counts={'E81':3688,'E82':209,'E86':400},source_public_hashes={b:sha(p)for b,p in sources.items()},generic_instruction_sha256=hashlib.sha256(generic.encode()).hexdigest(),generation_candidate_sha256=sha(h/'GENERATION_CANDIDATE.json'),source_bindings_sha256=sha(h/'GENERATION_SOURCE_BINDINGS.PRIVATE.json'),text_only_allowlist=['id','prompt'],all_original_prompt_prefixes_retained=True,E81_generic_prompt_reused_verbatim=True,E82_E86_full_prefix_plus_verbatim_generic=True,private_joins_and_labels_not_in_generation_packet=True,all_sources_final_read_position_verified=True,final_inventory_system_availability_pending=True,exact_wire_privacy_cost_admission_pending=True,generation_calls=0,judge_calls=0,reservations_usd=0)
(r/'results/g_agreement/i2/E107_SOURCE_PREFIX_CPU_AUDIT.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
