"""Clean extraction and actual preflight for fresh ladder and follow-on auxiliary assignments."""
import argparse,json,sys,tempfile,tarfile,time,subprocess,hashlib
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=json.loads(a.request.read_text());archives=dict(r['input_archives'],source={'path':r['source_archive'],'sha256':r['source_archive_sha256']});proofs=[]
 with tempfile.TemporaryDirectory(prefix='second-exact-') as tmp:
  root=Path(tmp)
  for name,v in archives.items():
   assert sha(v['path'])==v['sha256'];target=root/name;target.mkdir()
   with tarfile.open(v['path']) as t:t.extractall(target,filter='data')
  assets=root/'assets.json';assets.write_text('{}')
  for pod in r['pods']:
   now=time.time();caps={e:r['maximum_cumulative_GPU_seconds'][e]-80 for e in pod['experiments']};a0=dict(pod['assignment_schema'],pod_id='CPU_DRY_RUN_'+pod['name'],cohort_id='CPU_COHORT',pod_created_epoch=now,custody_start_epoch=now,caps=caps,prior_custody_seconds=dict.fromkeys(caps,0),absolute_deadline_epoch=now+sum(caps.values()),provider_deadline_epoch=now+sum(caps.values()))
   ass=root/(pod['name']+'.json');ass.write_text(json.dumps(a0));out=root/pod['name'];argv=[sys.executable,str(root/'source/results/g_agreement/understand/e62/job/second_worker.py'),'--assignment',str(ass),'--assets',str(assets),'--out',str(out),'--go',str(root/'GO.json'),'--dry-run']
   for e in r['input_archives']:argv+=['--'+e.lower()+'-inputs',str(root/e/'inputs')]
   result=subprocess.run(argv,cwd=root/'source',capture_output=True,text=True)
   if result.returncode:raise RuntimeError(result.stderr)
   proof=json.loads((out/'DRY_RUN.json').read_text());assert proof['status']=='PASS' and set(proof['experiments'])==set(pod['experiments']);proofs.append(dict(pod=pod['name'],**proof))
  (root/'E62/inputs/parity/INPUT_SEAL.json').unlink();argv[argv.index('--out')+1]=str(root/'negative');negative=subprocess.run(argv,cwd=root/'source',capture_output=True,text=True);assert negative.returncode and 'INPUT_SEAL.json' in negative.stderr
 report={'status':'PASS','source_commit':r['source_commit'],'archive_hashes':{e:v['sha256'] for e,v in archives.items()},'clean_extraction':True,'pod_preflights':proofs,'missing_parity_seal':'REJECTED','GPU_calls':0};a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print('EXACT_SECOND_WAVE_ASSIGNMENTS_PASS')
if __name__=='__main__':main()
