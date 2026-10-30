"""CPU-only frozen matcher intake; no paid calls, truth scoring or statistical analysis."""
from pathlib import Path
import datetime,hashlib,json,os,sys
sys.path.insert(0,str(Path.cwd()))
B=Path('results/g_agreement/understand/e97')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p.write_text(json.dumps(x,sort_keys=True,ensure_ascii=False,indent=2)+'\n');os.chmod(p,0o600)
def main():
 dest=Path('cache/g_agreement/understand/e97/judge_inventory_v1');assert not dest.exists(),'Do not rebuild frozen inventory'
 bank=json.loads((B/'BANK_SEAL.json').read_text())
 for n in ['MANIFEST.json','ROW_LIST.json','regex97.py','rows97.py']:
  assert sha(B/n)==bank['files'][n]
 manifest=json.loads((B/'MANIFEST.json').read_text());private=Path(manifest['private_labels']);assert sha(private)==manifest['files']['cache/bank_2026-10-28_v2/PRIVATE_LABELS.jsonl']
 labels=[json.loads(l)for l in private.read_text().splitlines()];assert len(labels)==6720
 tests={x['item_id']:x for x in labels if x['split']=='test'};assert len(tests)==3360
 rows={x['row']:x for x in json.loads((B/'ROW_LIST.json').read_text())['rows']};assert len(rows)==40
 sys.path.insert(0,str(B.resolve()));import regex97
 from projects.g_agreement.understand.blind_judge.rubric202 import original_ids
 candidates=[];mapping=[];classifications=[];source={};counts={}
 for reader,layer in [('oracle',44),('nla',42)]:
  root=Path('cache/g_agreement/understand/e97')/(reader+'_native_complete')/'out';seal=json.loads((root/'OUTPUT_SEAL.json').read_text());assert seal['status']=='COMPLETE'
  files=sorted((root/'records').glob('*.json'));assert len(files)==3360
  actual=set();unresolved=0
  for f in files:
   assert sha(f)==seal['files']['records/'+f.name]
   x=json.loads(f.read_text());iid=x['id'];assert iid==f.stem and iid in tests and iid not in actual;actual.add(iid)
   assert x['reader']==reader and x['reader_native_layer']==layer and x['repeat']==0
   row=rows[tests[iid]['row']];value=regex97.classify(row['row'],x['text'])
   jid=hashlib.sha256(('E97:'+reader+':'+iid).encode()).hexdigest()[:32]
   mapping.append(dict(id=jid,item_id=iid,reader=reader,row=row['row'],source_path=str(f.resolve()),source_sha256=sha(f),malformed=x['malformed']))
   classifications.append(dict(id=jid,regex_value=value,unresolved=value is None))
   if value is None:
    unresolved+=1;candidates.append(dict(id=jid,readout=x['text'],property=dict(definition=row['definition'],values=row['values'])))
  assert actual==set(tests);counts[reader]=dict(native_items=3360,unresolved_judge_units=unresolved)
  source[reader]=dict(output_seal_sha256=sha(root/'OUTPUT_SEAL.json'),native_closeout_sha256=sha(B/('I5_'+reader.upper()+'_NATIVE_COMPLETE_CLOSEOUT.json')))
 assert len({x['id']for x in mapping})==6720
 old_ids=original_ids([x['id']for x in candidates],'E97')
 dest.mkdir(parents=True);os.chmod(dest,0o700)
 for name,data in [('CANDIDATES.PRIVATE.json',candidates),('MAPPING.PRIVATE.json',mapping),('REGEX_CLASSIFICATIONS.PRIVATE.json',classifications),('ORIGINAL_IDS.PRIVATE.json',old_ids)]:write(dest/name,data)
 receipt=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),experiment='E97',scope='CPU_FROZEN_MATCHER_AND_UNRESOLVED_JUDGING_INTAKE_ONLY',native_records=6720,rows=40,counts=counts,unresolved_judge_units=len(candidates),original_rubric_seed20261028_count=len(old_ids),original_rubric_scope='25percent of selected unresolved judge units, ceil via frozen rubric202.original_ids(E97)',files={p.name:sha(p)for p in dest.iterdir()},native_sources=source,bank_seal_sha256=sha(B/'BANK_SEAL.json'),frozen_regex_sha256=sha(B/'regex97.py'),frozen_rows_sha256=sha(B/'rows97.py'),private_labels_source_sha256=sha(private),property_only_candidate_fields=['id','readout','property.definition','property.values'],channel_schema_pending=True,paid_calls=0,reservation=0,statistical_analysis=False,truth_accuracy_or_rates_computed=False)
 (B/'I5_JUDGING_INVENTORY_CPU_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:receipt[k]for k in ['native_records','unresolved_judge_units','original_rubric_seed20261028_count','counts']}))
if __name__=='__main__':main()
