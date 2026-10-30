from pathlib import Path
import json,hashlib,shutil,datetime
r=Path.cwd();old=r/'cache/g_agreement/i2/e81_judge_cpu_v1';new=r/'cache/g_agreement/i2/e81_judge_cpu_v3';assert not new.exists();new.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/results/g_agreement/understand/e49/job/CANDIDATES.json');bank=json.loads(source.read_text());rows=bank['rows'];items=json.loads((old/'JUDGE_PACKET.json').read_text());joins=json.loads((old/'JOIN_MAP.PRIVATE.json').read_text());index={x['id']:x for x in joins};changes=[]
for item in items:
 j=index[item['id']]
 if j['bank'].lower()!='e49':continue
 row=rows[j['row']];assert item['values']==dict(zip(['A','B'],row['spec']['values']))
 assert len(row['oracle'])==2 and all(len(p)==2 for p in row['oracle'])
 original=dict(item['values']);item['values']={'A':[p[0] for p in row['oracle']],'B':[p[1] for p in row['oracle']]}
 changes.append(dict(id=item['id'],row=j['row'],original_codes=original,frozen_original_phrasings=item['values']))
assert len(changes)==2352 and len(items)==7376
(new/'JUDGE_PACKET.json').write_text(json.dumps(items,indent=2,ensure_ascii=False)+'\n')
for name in ['JOIN_MAP.PRIVATE.json','ORIGINAL_IDS.json','E73_SOURCE_PACKET_VERIFICATION.private.json']:shutil.copy2(old/name,new/name);assert sha(old/name)==sha(new/name)
(new/'E49_VALUE_BINDING_DIFF.PRIVATE.json').write_text(json.dumps(changes,indent=2,ensure_ascii=False)+'\n')
original=json.loads((old/'JUDGE_PACKET.json').read_text());assert all({k:v for k,v in a.items() if k!='values'}=={k:v for k,v in b.items() if k!='values'} for a,b in zip(original,items));assert all(a==b for a,b in zip(original,items) if index[a['id']]['bank'].lower()!='e49')
receipt=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PROSPECTIVE_CPU_VALUE_DESCRIPTION_BINDING_REPAIR_BEFORE_ANY_JUDGE_CALL',reason='E49 machine state codes alone do not define semantic polarity for rows such as product comparison; use both original frozen Oracle candidate phrasings in their original A/B order.',original_v1_preserved=True,previous_source_seal_sha256=sha(old/'SOURCE_SEAL.json'),original_candidate_source_sha256=sha(source),original_candidate_source_frozen_before_scores=bank['frozen_before_scores'],changed_blind_records=2352,total_primary_records=7376,new_source_packet_sha256=sha(new/'JUDGE_PACKET.json'),all_ids_readouts_properties_unchanged=True,private_truth_join_bytes_unchanged=True,original_rubric_subset_bytes_unchanged=True,all_non_E49_records_unchanged=True,all_E49_phrasings_reused_verbatim_and_order_unchanged=True,no_generated_descriptions=True,no_outcome_conditioned_selection=True,rubric_route_output_limits_scope_unchanged=True,judge_calls=0,reservations_usd=0,cap_question_already_asked_once_total33_remains_pending=True)
(r/'results/g_agreement/i2/E81_E49_SEMANTIC_VALUE_BINDING_REPAIR.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
