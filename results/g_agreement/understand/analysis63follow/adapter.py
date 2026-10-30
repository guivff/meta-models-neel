"""E63 follow19 custody and lossless pool export; unchanged registered regex scorer."""
import sys,argparse,secrets,re,subprocess
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;U=HERE.parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(U/'e56/job'));sys.path.insert(0,str(U/'e63/job'))
from contract56 import read,dump,verify,seal,sha,require
from vendor_readerbench.io import load_bundle
from vendor_readerbench.e63 import validate_scope
from vendor_readerbench.score_reader import score
from vendor_readerbench.scoring import RUBRIC_HASHES
from native_nla512 import truncation_summary
COHORT='joint-a7fea77c-7279007d'

def unique(xs,key,expected):
 keys=[key(x) for x in xs];require(len(keys)==len(set(keys)) and set(keys)==set(expected),'exact unique grid')
def config(path):
 s=read(path);c=read(HERE/'COMMANDS.json');require(sha(path)==c['spec_sha256'],'sealed spec');verify(HERE,'SOURCE_SEAL.json',c['source_seal_sha256'])
 for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'dependency '+n)
 return s

def collect(s):
 r=read(s['receipt']);require(r['verified'] is True and r['experiment']=='E63','verified pull');root=Path(r['output']);o=verify(root,'OUTPUT_SEAL.json',r['output_seal_sha256']);q=read(HERE/'ACQUISITION_REQUEST.json');sh=next(x for x in q['shards'] if x['experiment']=='E63');inp=Path(s['inputs']);verify(inp,'INPUT_SEAL.json',sh['input_seal_sha256']);a=read(root/'ASSIGNMENT.json')
 require(o['status']=='COMPLETE' and o['experiment']=='E63' and o['shard']==0 and o['cohort_id']==COHORT and o['source_seal_sha256']==q['source_seal_sha256'] and o['input_seal_sha256']==sh['input_seal_sha256'],'follow19 output identity')
 require(o['pod_id']==r['pod_id']==a['pod_id'] and a['experiment']=='E63' and a['cohort_id']==COHORT and a['shard']==0 and a['gpu_count']==1,'assignment identity')
 require(a['prior_compute_seconds']>=0 and a['compute_cap_seconds']>0 and a['compute_cap_seconds']+a['prior_compute_seconds']==8650,'registered cumulative8650 cap')
 require(a['staging_cap_seconds']==900 and a.get('go_wait_cap_seconds',0)==0 and a['pod_created_epoch']<=a['staging_start_epoch'] and a['absolute_deadline_epoch']==a['staging_start_epoch']+900+a['compute_cap_seconds'],'staging and outer deadline')
 require(a['daily_budget_verified'] is True and 0<=a['projected_daily_USD']<=260,'historical budget')
 dep=a['dependency_receipt'];require(dep['verified'] is True and dep['cohort_id']==COHORT and len(dep['E57_output_seals'])==3 and all(re.fullmatch('[0-9a-f]{64}',x) for x in dep['E57_output_seals']),'E57 dependency')
 cap=root/'capture';c=verify(cap,'CAPTURE_SEAL.json',o['capture_seal_sha256']);items=read(inp/'items.json');require(c['experiment']=='E63' and c['cohort_id']==COHORT and c['input_seal_sha256']==sh['input_seal_sha256'] and read(cap/'items.order.json')==[x['id'] for x in items],'frozen real pool capture order')
 ready=read(root/'CAPTURE_READY.json');go=read(root/'GO_RECEIPT.json');t=read(root/'TIMING.json')
 for k in ('pod_id','cohort_id','capture_seals','input_seals'):require(go[k]==ready[k],'GO binding')
 require(go['pod_id']==a['pod_id'] and go['cohort_id']==COHORT and go['capture_seals']=={'E63':sha(cap/'CAPTURE_SEAL.json')} and go['input_seals']=={'E63':sh['input_seal_sha256']} and go['reader_launch_authorized'] is True,'capture-bound GO')
 require(re.fullmatch('[0-9a-f]{40}',go['forecast_commit']) and re.fullmatch('[0-9a-f]{64}',go['forecast_seal_sha256']),'forecast identity')
 require(a['staging_start_epoch']<=ready['ready_epoch']<=go['issued_epoch']<=a['staging_start_epoch']+900,'capture before GO inside staging')
 require(t['compute_from_GO']==go['issued_epoch'] and t['deadline_epoch']==go['issued_epoch']+a['compute_cap_seconds'] and go['issued_epoch']<=t['completed_epoch']<=t['deadline_epoch'],'GO compute clock')
 require(read(root/'parity/PARITY_RESULT.json')['status']=='PASS' and read(root/'FORECAST.json')['status']=='ADMIT','parity/self-admission')
 # Exact same deterministic100-job grid as second_worker.jobs_for; no model import.
 expected=[]
 for reader in ('oracle','nla'):
  for arm in ('random','shuffled'):
   for start in range(0,200,8):expected.append(dict(exp='E63',reader=reader,kind='pool',units=[{'id':f'{arm}:{i:03d}'} for i in range(start,start+8)],phase='E63_'+reader+'_native',arm=arm,number=len(expected)))
 require(read(root/'JOB_GRID.json')==expected and read(root/'COMPLETED.json')==list(range(100)),'all100 frozen jobs complete once')
 rows=[]
 for j in expected:
  v=read(root/'jobs'/f'{j["number"]:06d}.json');require(len(v)==8,'eight vectors/job')
  for x,u in zip(v,j['units']):
   require(x['vector_id']==u['id'] and x['reader']==j['reader'] and x['pool']==j['arm'] and x['layer']==(44 if j['reader']=='oracle' else 42) and x['repeat']==0 and isinstance(x['text'],str),'unaltered native pool identity')
   rows.append(dict(id=x['reader']+':'+x['vector_id'],item_id=x['vector_id'],reader=x['reader'],arm=x['pool'],layer=x['layer'],repeat=0,text=x['text'],raw=x.get('raw',x['text'])))
 unique(rows,lambda x:x['id'],[f'{r}:{arm}:{i:03d}' for r in ('oracle','nla') for arm in ('random','shuffled') for i in range(200)])
 return root,rows

def select(rows):
 selected=[]
 for reader in ('oracle','nla'):
  pool=sorted((x for x in rows if x['reader']==reader),key=lambda x:x['id']);require(len(pool)==400,'two200-vector pools, single readout')
  rng=np.random.default_rng(20261027);selected.extend(pool[int(i)] for i in rng.choice(400,200,replace=False))
 return selected

def blind(s,root,rows):
 require(sha(HERE/'JUDGE_RUBRIC.md')==RUBRIC_HASHES['D5'],'unchanged D5 rubric');out=Path(s['blind_out']);keypath=Path(s['private_key'])
 require(not keypath.resolve().is_relative_to(out.resolve()),'private key separate')
 require(subprocess.run(['git','check-ignore','-q',str(keypath)],cwd=ROOT).returncode==0,'private key ignored')
 require(not out.exists() and not keypath.exists(),'export once, no overwrite')
 chosen=select(rows);rng=np.random.default_rng(20261027);packet=[];key=[]
 for i in rng.permutation(len(chosen)):
  x=chosen[int(i)];opaque=secrets.token_hex(16);packet.append(dict(id=opaque,property='What this readout explicitly describes',values={},readout=x['text']));key.append(dict(x,opaque_id=opaque))
 out.mkdir(parents=True,exist_ok=False);keypath.parent.mkdir(parents=True,exist_ok=True);dump(keypath,key);keypath.chmod(0o600);dump(out/'JUDGE_PACKET.json',packet);(out/'JUDGE_RUBRIC.md').write_bytes((HERE/'JUDGE_RUBRIC.md').read_bytes())
 seal(out,'RESULT_SEAL.json',dict(job='E63_RP2',status='AWAITING_SEALED_E56_ROUTE_AND_JUDGMENTS',n=400,receipt_sha256=sha(s['receipt']),output_seal_sha256=sha(root/'OUTPUT_SEAL.json'),private_key_sha256=sha(keypath),rubric_sha256=sha(HERE/'JUDGE_RUBRIC.md')))
 # Separate lossless full800 pool export for the existing row/regex normalizer.
 full=Path(s['pool_out']);full.mkdir(parents=True,exist_ok=False);dump(full/'POOLS.json',rows);dump(full/'NLA_TRUNCATION.json',truncation_summary([dict(x,pool=x['arm']) for x in rows if x['reader']=='nla'],row_key='pool'));seal(full,'POOL_SEAL.json',dict(experiment='E63',output_seal_sha256=sha(root/'OUTPUT_SEAL.json'),receipt_sha256=sha(s['receipt'])))

def match_bundle(rows,data):
 validate_scope(data);lookup={x['id']:x for x in rows};unique(data['placebo'],lambda x:x['reader']+':'+x['item_id'],lookup)
 for x in data['placebo']:
  y=lookup[x['reader']+':'+x['item_id']]
  require(all(x[k]==y[k] for k in ('text','reader','item_id','arm','layer','repeat')),'lossless normalized pool identity/text')

def analyze(s,root,rows):
 br=read(s['bundle_receipt']);require(br['verified'] is True and br['e63_output_seal_sha256']==sha(root/'OUTPUT_SEAL.json'),'normalizer exact output binding');data,_=load_bundle(s['bundle'],br['input_seal_sha256']);match_bundle(rows,data)
 guard=ROOT/'cache/g_agreement/understand/e63/REGEX_ANALYSIS_ONCE.json';out=Path(s['analysis_out']);require(not out.exists(),'output already exists');guard.parent.mkdir(parents=True,exist_ok=True)
 with guard.open('x') as f:f.write(sha(HERE/'SPEC.json')+'\n')
 try:
  result={r:score(data,r) for r in ('oracle','nla')};out.mkdir(parents=True,exist_ok=False);dump(out/'REGEX_RESULTS.json',result);dump(out/'R_P2_STATUS.json',dict(status='SEPARATE_W_INTERNALS_CODING_COMMAND',no_judge_calls=True,matching_reader_MISSED_reference_required=True));seal(out,'ANALYSIS_SEAL.json',dict(experiment='E63',status='COMPLETE_ONCE',input_seal_sha256=br['input_seal_sha256'],output_seal_sha256=sha(root/'OUTPUT_SEAL.json'),adapter_source_seal_sha256=sha(HERE/'SOURCE_SEAL.json')))
 except BaseException as error:dump(guard.with_name('REGEX_FAILURE.json'),dict(error_type=type(error).__name__));raise

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--mode',choices=['verify','blind','analyze'],required=True);a=p.parse_args();s=config(a.spec);root,rows=collect(s)
 if a.mode=='blind':blind(s,root,rows)
 elif a.mode=='analyze':analyze(s,root,rows)
if __name__=='__main__':main()
