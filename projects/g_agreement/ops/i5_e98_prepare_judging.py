"""E98: exact source-bound E57/E59 regex-first/count/value intake; no statistics."""
from pathlib import Path
import json,hashlib,os,sys,datetime,importlib.util
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.understand.blind_judge.privacy79 import redact
from projects.g_agreement.understand.blind_judge.rubric202 import original_ids
from projects.g_agreement.ops.e98_frozen_regex620 import apply as frozen_regex
B=Path('results/g_agreement/understand/e98');ROOT=Path.cwd().parent

def main():
 dest=Path('cache/g_agreement/understand/e98/judge_packet_v2');assert not dest.exists(),'Never rebuild final packet'
 owner=ROOT/'wt-internals-b/results/g_agreement/understand/blind_judge/e98_bank';binding=read(owner/'SOURCE_BINDINGS.json');pins=binding['bindings']
 # Exact original producer source values/aliases, count metadata, and regex policies.
 planpath=Path(pins['original_E57_plan']['local_path']);assert sha(planpath)==pins['original_E57_plan']['sha256'];plan=read(planpath)
 catalogpath=Path('results/g_agreement/understand/e76/REGEX_CATALOG.json');assert sha(catalogpath)==pins['regex_catalog']['sha256'];catalog={(x['bank'],x['row']):x for x in read(catalogpath)['rows']}
 counts_source=B.parent/'e57/job/counts57.py';assert sha(counts_source)==pins['original_count_detector']['sha256'];assert sha(Path(__file__).with_name('e98_frozen_regex620.py'))=='620a763fbc270dc30c73ef353e7b68cb85fc765932573f32ed2e96bf356e5f6d'
 spec=importlib.util.spec_from_file_location('original_counts57',counts_source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 port=read(B/'PORT_RECEIPT.json');keypath=Path('cache/g_agreement/understand/e98/ported_v1/KEY.PRIVATE.json');assert sha(keypath)==port['private_key_sha256'];keys=read(keypath);test={x['id']:x for x in keys if x['split']=='test'};assert len(keys)==4368 and len(test)==2184
 sources={};sourcepins={}
 for bank in ['E57','E59']:
  m=read(B.parent/bank/'FREEZE_MANIFEST.json');p=Path(m['bank_directory']);assert sha(p/'BANK_SEAL.json')==port['source_banks'][bank]['bank_seal_sha256'];seal=read(p/'BANK_SEAL.json');assert sha(p/'items.PRIVATE.json')==port['source_banks'][bank]['items_sha256']
  sources[bank]=dict(path=p,seal=seal,items={x['id']:x for x in read(p/'items.PRIVATE.json')});sourcepins[bank]=dict(bank_seal_sha256=sha(p/'BANK_SEAL.json'),items_sha256=sha(p/'items.PRIVATE.json'))
 vpath=sources['E59']['path']/'VALIDATION.json';assert sha(vpath)==sources['E59']['seal']['files']['VALIDATION.json'];validation=read(vpath)
 native=Path('cache/g_agreement/understand/e98/reader_native_complete/out');nseal=read(native/'OUTPUT_SEAL.json');assert nseal['status']=='COMPLETE';assert {p.stem for p in(native/'records').glob('*.json')}==set(test)
 calls=[];mapping=[];counts=[];resolved=[];perrow={};nonbinary={}
 for iid,x in sorted(test.items()):
  original=sources[x['source_bank']]['items'][x['source_id']];assert x['text']==original['text']and hashlib.sha256(original['text'].encode()).hexdigest()==x['source_text_sha256'];assert x['label']==original['label']and x['split']==original['split']
  p=native/'records'/(iid+'.json');assert sha(p)==nseal['files']['records/'+iid+'.json'];r=read(p);assert r['id']==iid;row=x['feature'];bank=x['source_bank'];perrow[row]=perrow.get(row,0)+1
  mapping.append(dict(id=iid,source_bank=bank,source_id=x['source_id'],row=row,label=x['label'],native_sha256=sha(p),source_text_sha256=x['source_text_sha256']))
  if bank=='E57'and row in ['category_switch','capacity_list']:
   value=mod.count_item([dict(reader='oracle',unit_id=x['source_id'],feature=row,repeat=0,text=r['text'])],plan['count_metadata'][x['source_id']]);value.pop('unit_id');counts.append(dict(id=iid,measurement=value));continue
  if bank=='E57':values=plan['judge_values'][x['source_id']];prop=plan['rows'][row]['canonical_row']
  else:values=validation[row]['registered_reader_value_words'];prop=row
  assert len(values)==2;values=dict(A=values[0],B=values[1]);result=frozen_regex(r['text'],values,catalog.get((bank,row)))
  if result is None:calls.append(dict(id=iid,readout=r['text'],property=dict(definition=prop,values=values)))
  else:resolved.append(dict(id=iid,category='states_value',values=result,source='frozen_regex620/E76catalog',evidence=r['text']))
  if x['label'] is None:nonbinary[row]=nonbinary.get(row,0)+1
 assert len(mapping)==2184 and len(counts)==168 and len(calls)+len(resolved)+168==2184 and len(perrow)==26 and all(n==84 for n in perrow.values())and nonbinary=={'focus_none':84}
 copied,audit=redact(calls,'E98',addresses=True);assert [x['id']for x in calls]==[x['id']for x in copied]
 for a,b in zip(calls,copied):assert a['property']==b['property']
 dest.mkdir(parents=True);os.chmod(dest,0o700)
 data={'CANDIDATES.PRIVATE.json':copied,'RAW_CANDIDATES.PRIVATE.json':calls,'MAPPING.PRIVATE.json':mapping,'COUNT_MEASURES.json':counts,'REGEX_RESOLVED.json':resolved,'NATIVE_IDS.json':sorted(test),'PATH_REDACTION_AUDIT.PRIVATE.json':audit,'ORIGINAL_IDS.PRIVATE.json':original_ids([x['id']for x in calls],'E98')}
 for n,v in data.items():write(dest/n,v);os.chmod(dest/n,0o600)
 ns=native/'OUTPUT_SEAL.json';inp=dict(experiment='E98',status='FROZEN_READY',labels_cpu_only=True,native_per_reader_counts={'oracle':2184},registered_rows=26,binary_items=1932,nonbinary_items=252,registered_count_items=168,mention_only_items=84,judge_unresolved_items=len(calls),regex_resolved_items=len(resolved),native_seal_sha256=sha(ns),source_seals=[dict(seal=str(ns.resolve()),sha256=sha(ns))],files={n:sha(dest/n)for n in ['CANDIDATES.PRIVATE.json','COUNT_MEASURES.json','REGEX_RESOLVED.json','NATIVE_IDS.json','PATH_REDACTION_AUDIT.PRIVATE.json']},source_binding_sha256=sha(owner/'SOURCE_BINDINGS.json'),original_source_pins=sourcepins,original_E57_plan_sha256=sha(planpath),original_catalog_sha256=sha(catalogpath),regex_apply_sha256=sha(Path(__file__).with_name('e98_frozen_regex620.py')),counts_source_sha256=sha(counts_source))
 write(dest/'INPUT_SEAL.json',inp);os.chmod(dest/'INPUT_SEAL.json',0o600)
 receipt=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),experiment='E98',native_items=2184,rows=26,dropped_rows=[],binary_items=1932,nonbinary_items=252,registered_count_items=168,mention_only_items=84,judge_unresolved_items=len(calls),regex_resolved_items=len(resolved),original_rubric_check=len(data['ORIGINAL_IDS.PRIVATE.json']),source_binding_sha256=sha(owner/'SOURCE_BINDINGS.json'),source_pins=sourcepins,original_E57_plan_sha256=sha(planpath),original_E59_value_binding='VALIDATION.registered_reader_value_words unchanged aliases',regex_apply_sha256=inp['regex_apply_sha256'],catalog_sha256=sha(catalogpath),counts_source_sha256=sha(counts_source),input_seal=str((dest/'INPUT_SEAL.json').resolve()),input_sha256=sha(dest/'INPUT_SEAL.json'),private_files={n:sha(dest/n)for n in data},judge_copy_redacted_records=audit['redacted_records'],audit_sha256=sha(dest/'PATH_REDACTION_AUDIT.PRIVATE.json'),paid_calls=0,statistics_computed=False,v1_prototype='SUPERSEDED_BEFORE_ANY_PAID_CALL; preserved guarded',labels_cpu_only=True)
 write(B/'I5_JUDGING_INTAKE_CPU_RECEIPT.json',receipt);print(json.dumps({k:receipt[k]for k in ['native_items','judge_unresolved_items','regex_resolved_items','registered_count_items','original_rubric_check','judge_copy_redacted_records']}))
if __name__=='__main__':main()
