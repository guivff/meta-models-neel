"""Mandatory CPU check of the exact source/input tarballs before every profile reissue."""
import argparse,hashlib,json,subprocess,sys,tarfile,tempfile,time
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=json.loads(a.request.read_text())
 for path,digest in [(r['source_archive'],r['source_archive_sha256']),(r['input_archive']['path'],r['input_archive']['sha256'])]:
  if sha(path)!=digest:raise ValueError('exact archive hash mismatch')
 with tempfile.TemporaryDirectory(prefix='e56-exact-pod-') as tmp:
  root=Path(tmp);source=root/'source';inputs=root/'pod_inputs';source.mkdir();inputs.mkdir()
  for archive,target in [(r['source_archive'],source),(r['input_archive']['path'],inputs)]:
   with tarfile.open(archive) as t:t.extractall(target,filter='data')
  now=time.time();ass=dict(r['assignment_schema'],pod_id='CPU_DRY_RUN',pod_created_epoch=now,absolute_deadline_epoch=now+1800)
  assignment=root/'assignment.json';assignment.write_text(json.dumps(ass));assets=root/'assets.json';assets.write_text(json.dumps({'CPU_DRY_RUN_MODEL_LOADING_STUBBED':True}))
  argv=[sys.executable,str(source/'results/g_agreement/understand/e56/job/profile_single.py'),'--inputs',str(inputs/'inputs'),'--assets',str(assets),'--assignment',str(assignment),'--out',str(root/'out'),'--dry-run']
  subprocess.run(argv,cwd=source,check=True,capture_output=True,text=True)
  proof=json.loads((root/'out/DRY_RUN.json').read_text());assert proof['status']=='PASS' and proof['parity_inputs']==252
  # Regression: missing nested seal MUST fail before any model loading.
  (inputs/'inputs/parity/INPUT_SEAL.json').unlink();negative=list(argv);negative[negative.index('--out')+1]=str(root/'negative')
  result=subprocess.run(negative,cwd=source,capture_output=True,text=True)
  assert result.returncode!=0 and 'INPUT_SEAL.json' in result.stderr,'missing parity seal must be rejected'
 report={'status':'PASS','source_archive_sha256':r['source_archive_sha256'],'input_archive_sha256':r['input_archive']['sha256'],'source_commit':r['source_commit'],'clean_extraction':True,'worker_preflight':'REAL','source_input_dependency_parity_validation':'REAL','model_loading':'STUBBED','GPU_calls':0,'missing_parity_seal_regression':'PASS','dry_run':proof}
 a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print('EXACT_ARCHIVE_DRY_RUN_PASS')
if __name__=='__main__':main()
