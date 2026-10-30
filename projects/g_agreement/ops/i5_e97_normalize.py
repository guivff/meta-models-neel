"""E97 complete-only CPU joins/schema normalization; no effect/CI/forecast score.
Full primary/old seals and closed custody precede loading private target labels.
"""
from pathlib import Path
import json,hashlib,os,datetime,subprocess,sys,shutil
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.ops.i5_e97_rt1_gate import validate_terminal
from missingness import validate_judgment
ROOT=Path.cwd();B=ROOT/'results/g_agreement/understand/e97';DEST=ROOT/'cache/g_agreement/understand/e97/rt1_normalization_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def assemble(mapping,labels,rows,primary,regex,copies,native):
 result=[]
 for x in sorted(mapping,key=lambda x:x['id']):
  iid=x['id'];lab=labels[x['item_id']]
  if lab['row']!=x['row']or lab['label']not in ('A','B')or lab['value']!=rows[x['row']]['values'][lab['label']]:raise ValueError('exact frozen target/polarity/row binding')
  if regex[iid]is None:
   code=primary[iid];text=copies[iid];source='judge'
  else:
   if regex[iid]not in ('A','B'):raise ValueError('frozen regex output')
   text=native[iid];code=dict(id=iid,category='states_value',values=[regex[iid]],evidence=text);source='frozen_regex'
  if code['id']!=iid:raise ValueError('exact code ID binding')
  code={k:code[k]for k in ('id','category','values','evidence')};validate_judgment(code,text)
  result.append(dict(id=iid,item_id=x['item_id'],reader=x['reader'],row=x['row'],label=lab['label'],code=code,code_source=source,malformed=x['malformed'],original_native_sha256=x['source_sha256'],judged_text_sha256=hashlib.sha256(text.encode()).hexdigest()))
 return result

def main():
 assert not DEST.exists(),'never rebuild normalized input'
 closeout=B/'I5_JUDGMENT_COMPLETE_CLOSEOUT.json';proof=read(closeout);validate_terminal(proof)
 q=ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E97/judgments';s=read(q/'JUDGMENT_SEAL.json');assert s['bank']=='E97'and s['primary_records']==6668 and s['old_rubric_records']==1667 and s['route_verified']and s['transport217c2_finalized'];assert sha(q/'JUDGMENT_SEAL.json')==proof['judgment_seal_sha256']
 for n,h in s['files'].items():assert sha(q/n)==h,n
 pub=ROOT/'results/g_agreement/sealed/E97_JUDGMENTS_COMPLETE/SEAL.json';assert read(pub)['files']['CLOSEOUT.json']==sha(closeout)
 freeze=read(B/'I5_RT1_COMPLETE_ADAPTER_SOURCE_FREEZE.json');assert freeze['committed_epoch']<(q/'JUDGMENT_SEAL.json').stat().st_mtime,'source must predate final bank seal'
 for n,h in freeze['files'].items():
  assert sha(ROOT/n)==h;assert hashlib.sha256(subprocess.check_output(['git','show',freeze['commit']+':'+n],cwd=ROOT)).hexdigest()==h
 inv=ROOT/'cache/g_agreement/understand/e97/judge_inventory_v1';cpu=read(B/'I5_JUDGING_INVENTORY_CPU_RECEIPT.json')
 for n,h in cpu['files'].items():assert sha(inv/n)==h,n
 bank=read(B/'BANK_SEAL.json')
 for n in ['MANIFEST.json','ROW_LIST.json','regex97.py','rows97.py']:assert sha(B/n)==bank['files'][n]
 manifest=read(B/'MANIFEST.json');labelpath=Path(manifest['private_labels']);assert sha(labelpath)==manifest['files']['cache/bank_2026-10-28_v2/PRIVATE_LABELS.jsonl']==cpu['private_labels_source_sha256']
 labels=[json.loads(l)for l in labelpath.read_text().splitlines()if l.strip()];assert len(labels)==6720;tests={x['item_id']:x for x in labels if x['split']=='test'};assert len(tests)==3360
 mapping=read(inv/'MAPPING.PRIVATE.json');assert len(mapping)==6720 and len({x['id']for x in mapping})==6720
 rows={x['row']:x for x in read(B/'ROW_LIST.json')['rows']};assert len(rows)==40
 cls=read(inv/'REGEX_CLASSIFICATIONS.PRIVATE.json');regex={x['id']:x['regex_value']for x in cls};assert set(regex)=={x['id']for x in mapping};unresolved={i for i,v in regex.items()if v is None};assert len(unresolved)==6668
 primary={x['id']:x for x in read(q/'PRIMARY.json')};old=read(q/'ORIGINAL.json');oldids=set(read(inv/'ORIGINAL_IDS.PRIVATE.json'));assert set(primary)==unresolved and len(old)==1667 and {x['id']for x in old}==oldids and oldids<=unresolved
 packet=ROOT/'cache/g_agreement/understand/e97/judge_copy_v1';assert sha(packet/'INPUT_SEAL.json')==s['input_sha256']
 for n,h in read(packet/'INPUT_SEAL.json')['files'].items():assert sha(packet/n)==h,n
 copies={x['id']:x['readout']for x in read(packet/'CANDIDATES.PRIVATE.json')};assert set(copies)==unresolved
 native={}
 for x in mapping:
  p=Path(x['source_path']);assert sha(p)==x['source_sha256'];v=read(p);assert v['id']==x['item_id']and v['reader']==x['reader'];assert v['reader_native_layer']==(44 if x['reader']=='oracle'else 42);native[x['id']]=v['text']
 records=assemble(mapping,tests,rows,primary,regex,copies,native)
 for x in old:validate_judgment(x,copies[x['id']])
 audit=read(packet/'PATH_REDACTION_AUDIT.PRIVATE.json');affected=sorted(x['id']for x in audit['affected']);assert len(affected)==227 and set(affected)==set(s['redacted_opaque_ids'])
 fref=read(B/'E97_WLENS_FORECAST_RECEIPT_20261028.json');fp=Path(fref['forecast_path']);assert sha(fp)==fref['forecast_sha256']=='5f099f9d84246fc4039e4f793844b67de498aedf368645af95d7f4bbcff23485';f=read(fp);forecast={x['row']:x for x in f['rows']};assert set(forecast)==set(rows)
 DEST.mkdir(parents=True);os.chmod(DEST,0o700)
 values={'ITEM_CODES.PRIVATE.json':records,'OLD_CODES.json':old,'ROWMETA.json':rows,'FORECAST_BY_ROW.json':forecast,'AFFECTED_IDS.json':affected}
 for n,v in values.items():
  (DEST/n).write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n');os.chmod(DEST/n,0o600)
 shutil.copyfile(fp,DEST/'ORIGINAL_FORECAST.json');os.chmod(DEST/'ORIGINAL_FORECAST.json',0o600);assert sha(DEST/'ORIGINAL_FORECAST.json')==fref['forecast_sha256']
 refs={k:dict(path=str(p.resolve()),sha256=sha(p))for k,p in {'terminal_receipt':closeout,'judgment_seal':q/'JUDGMENT_SEAL.json','item_codes':DEST/'ITEM_CODES.PRIVATE.json','old_codes':DEST/'OLD_CODES.json','rowmeta':DEST/'ROWMETA.json','forecast':DEST/'FORECAST_BY_ROW.json','original_forecast':fp,'affected_ids':DEST/'AFFECTED_IDS.json','bank_seal':B/'BANK_SEAL.json','row_list':B/'ROW_LIST.json','source_freeze':B/'I5_RT1_COMPLETE_ADAPTER_SOURCE_FREEZE.json'}.items()}
 receipt=dict(status='FULL_TERMINAL_NORMALIZATION_NO_EFFECT_STATISTICS',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native_records=6720,primary=6668,regex_resolved=52,old_rubric=1667,affected=227,private_label_sha256=sha(labelpath),frozen_bank_sha256=sha(B/'BANK_SEAL.json'),judgment_seal_sha256=sha(q/'JUDGMENT_SEAL.json'),refs=refs,code_freeze_commit=freeze['commit'],source_sha256=sha(__file__),row_rates_computed=False,BA_computed=False,bootstrap_run=False,once_guard_consumed=False)
 receiptpath=B/'I5_RT1_TERMINAL_NORMALIZATION_RECEIPT.json';receiptpath.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');refs['normalization_receipt']=dict(path=str(receiptpath.resolve()),sha256=sha(receiptpath))
 plan=dict(experiment='E97_R_T1',registration='§205(5)',input_format='E97_ITEM_CODES_V1',status='FINAL_INPUT_BOUND_COMMIT_BEFORE_FIXED_ONCE',primary_rule_panel='primary',affected_exclusion_panel_role='SENSITIVITY_ONLY_CANNOT_REPLACE_PRIMARY',code=freeze['files'],refs=refs,source_freeze_commit=freeze['commit'],rule='Oracle JBA-taxonomyBA>=.10 and paired-rowCI lower>0; falsifierdelta<=0; bothreaders/agreement; full40rows, primary+affected-excluded; old1667matchedcomparisononly',command='science python3.12 projects/g_agreement/ops/i5_e97_rt1_gate.py --plan results/g_agreement/understand/e97/RT1_FINAL_INPUT_PLAN.json',E75_pool_unchanged=True)
 (B/'RT1_FINAL_INPUT_PLAN.json').write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n');print('Full6720 target/code joins normalized afterterminalseal; NO rates/BA/bootstrap/onceclaim. Commit finalplan before execution.')
if __name__=='__main__':main()
