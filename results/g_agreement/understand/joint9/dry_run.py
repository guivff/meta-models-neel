"""Extract exact source and resume inputs, preflight all nine real shard assignments."""
import json,sys,tempfile,subprocess,tarfile,time,argparse,hashlib
from pathlib import Path
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=json.loads(a.request.read_text());proof=[]
 with tempfile.TemporaryDirectory(prefix='joint9-exact-') as tmp:
  root=Path(tmp)
  for name,path,digest in [('source',r['source_archive'],r['source_archive_sha256']),('data',r['input_archive'],r['input_archive_sha256'])]:
   assert h(path)==digest;target=root/name;target.mkdir()
   with tarfile.open(path) as t:t.extractall(target,filter='data')
  assets=root/'assets.json';assets.write_text('{}')
  for sh in r['shards']:
   now=time.time();ass=dict(sh['assignment_schema'],pod_id='CPU_DRY_RUN',pod_created_epoch=now,deadline_epoch=now+sh['cap_seconds'],daily_budget_verified=True,projected_daily_USD=144.2);ap=root/'assignment.json';ap.write_text(json.dumps(ass));out=root/(sh['experiment']+str(sh['shard']));argv=[sys.executable,str(root/'source/results/g_agreement/understand/joint9/runtime.py'),'--inputs',str(root/'data/inputs'),'--assignment',str(ap),'--assets',str(assets),'--out',str(out),'--go',str(root/'GO.json'),'--source-sha',r['source_seal_sha256'],'--input-sha',r['input_seal_sha256'],'--dry-run'];x=subprocess.run(argv,cwd=root/'source',capture_output=True,text=True)
   if x.returncode:raise RuntimeError(x.stderr)
   proof.append(json.loads((out/'DRY_RUN.json').read_text()))
  (root/'data/inputs/parity/INPUT_SEAL.json').unlink();argv[argv.index('--out')+1]=str(root/'negative');x=subprocess.run(argv,cwd=root/'source',capture_output=True,text=True);assert x.returncode and 'INPUT_SEAL.json' in x.stderr
 a.report.write_text(json.dumps({'status':'PASS','source_archive_sha256':r['source_archive_sha256'],'input_archive_sha256':r['input_archive_sha256'],'nine_shards':proof,'missing_parity_seal':'REJECTED','GPU_calls':0},indent=2)+'\n');print('NINE_EXACT_ARCHIVE_PREFLIGHTS_PASS')
if __name__=='__main__':main()
