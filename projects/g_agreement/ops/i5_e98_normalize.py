"""E98 schema translation only. No rates, truth scoring, bootstrap or once claim.
Count-only measurements remain typed counts; never fabricate a judge category.
"""
import json,os,sys,hashlib,datetime
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path.cwd()))
ROOT=Path.cwd()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n');os.chmod(p,0o600)
def combine(primary,regex,counts,ids):
 def codes(xs):
  out={}
  for x in xs:
   if x['id'] in out:raise ValueError('duplicate judgment')
   if x['category'] not in ('states_value','names_property_without_value','exhibits','silent','UNPARSEABLE'):raise ValueError('original category required')
   out[x['id']]={k:x[k]for k in ('id','category','values','evidence')}
  return out
 p,r=codes(primary),codes(regex);c={x['id']:x['measurement']for x in counts}
 if len(c)!=len(counts)or set(p)&set(r)or (set(p)|set(r))&set(c)or set(p)|set(r)|set(c)!=set(ids):raise ValueError('exact disjoint judge/regex/count grid')
 return p|r,c

def main():
 dest=ROOT/'cache/g_agreement/understand/e98/analysis_normalization_v1';assert not dest.exists(),'no normalization replay'
 q=ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E98/judgments';s=read(q/'JUDGMENT_SEAL.json');assert s['terminal']and s['primary_records']==1785 and s['old_rubric_records']==447
 for n,h in s['files'].items():assert sha(q/n)==h
 packet=ROOT/'cache/g_agreement/understand/e98/judge_packet_v2';assert sha(packet/'INPUT_SEAL.json')==s['input_sha256'];mapping=read(packet/'MAPPING.PRIVATE.json');ids={x['id']for x in mapping};assert len(mapping)==len(ids)==2184
 judgments,counts=combine(read(q/'PRIMARY.json'),read(q/'REGEX_RESOLVED.json'),read(q/'COUNT_MEASURES.json'),ids)
 old=read(q/'ORIGINAL.json');assert {x['id']for x in old}==set(read(packet/'ORIGINAL_IDS.PRIVATE.json'))and len(old)==447
 native={};group=defaultdict(list);nroot=ROOT/'cache/g_agreement/understand/e98/reader_native_complete/out';ns=read(nroot/'OUTPUT_SEAL.json');assert sha(nroot/'OUTPUT_SEAL.json')==s['native_seal_sha256']
 for x in mapping:
  p=nroot/'records'/(x['id']+'.json');assert sha(p)==x['native_sha256']==ns['files']['records/'+x['id']+'.json'];v=read(p);assert v['id']==x['id'];native[x['id']]=v['text'];group[(x['source_bank'],x['row'])].append(dict(id=x['id'],label=x['label'],source_id=x['source_id']))
 units=[dict(bank=b,row=r,binary=r not in ('capacity_list','category_switch','focus_none'),items=sorted(xs,key=lambda x:x['id']))for (b,r),xs in sorted(group.items())];assert len(units)==26 and sum(x['binary']for x in units)==23 and all(len(u['items'])==84 for u in units)
 qwen={};source={}
 paths={'E57':ROOT.parent/'wt-wmech/cache/g_agreement/understand/e56_e57/verified_pull_single_v1/e57/analysis_once','E59':ROOT.parent/'wt-wmech/cache/g_agreement/understand/analysis5968_verified/E59/analysis_once'}
 for b,p in paths.items():
  seal=read(p/'ANALYSIS_SEAL.json')
  for n,h in seal['files'].items():assert sha(p/n)==(h['sha256']if isinstance(h,dict)else h)
  result=read(p/'RESULTS.json');co=read(p/'COUNTS.json')if (p/'COUNTS.json').exists()else []
  source[b]=dict(results_path=str(p/'RESULTS.json'),results_sha256=sha(p/'RESULTS.json'),analysis_seal_path=str(p/'ANALYSIS_SEAL.json'),analysis_seal_sha256=sha(p/'ANALYSIS_SEAL.json'),counts_sha256=sha(p/'COUNTS.json')if co else None)
  for u in [x for x in units if x['bank']==b]:
   key=b+'|'+u['row'];rate=result['rates'].get('oracle|'+u['row']);original_ids={x['source_id']for x in u['items']}
   qwen[key]=dict(original_signed_metric=rate,signed_metric_present=rate is not None,original_count_records=[x for x in co if x['reader']=='oracle'and x['feature']==u['row']and x['unit_id']in original_ids],source=source[b],no_baseline_rerun=True)
 forecast=ROOT/'results/g_agreement/understand/e98/wlens_forecast/E98_JFORECAST.json';assert sha(forecast)=='2cd5727a33255c4295c3130948631c373733b9bdc246c31d6063e3b9b2947c1d'
 dest.mkdir(parents=True);os.chmod(dest,0o700)
 payload={'UNITS.PRIVATE.json':units,'JUDGMENTS.json':judgments,'COUNT_MEASURES.json':counts,'NATIVE.json':native,'ORIGINAL.json':old,'FORECAST.json':read(forecast),'ORIGINAL_QWEN.json':qwen}
 for n,v in payload.items():dump(dest/n,v)
 receipt=dict(status='NORMALIZED_NO_OUTCOME_STATISTICS_OWNER_FINAL_SCHEMA_PENDING',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=sha(__file__),judgment_seal_sha256=sha(q/'JUDGMENT_SEAL.json'),native_seal_sha256=s['native_seal_sha256'],input_sha256=s['input_sha256'],mapping_sha256=sha(packet/'MAPPING.PRIVATE.json'),normalized_files={n:sha(dest/n)for n in payload},items=2184,rows=26,binary_rows=23,judge_or_regex_items=len(judgments),count_only_items=len(counts),original_rubric=447,original_qwen_source=source,no_fabricated_judgments=True,analysis_run=False,once_claim=False)
 dump(dest/'NORMALIZATION_RECEIPT.json',receipt);pub=ROOT/'results/g_agreement/understand/e98/I5_ANALYSIS_NORMALIZATION_RECEIPT.json';pub.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print('Normalized exact 2184 records without statistics or fabricated count judgments')
if __name__=='__main__':main()
