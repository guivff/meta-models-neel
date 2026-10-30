"""Exact archive preflight on actual3192vectors with model loading stubbed."""
import sys,tempfile,tarfile,subprocess,time
from pathlib import Path
from worker import *
def run():
 r=read(HERE/'REQUEST.json')
 with tempfile.TemporaryDirectory(prefix='e79-exact-') as tmp:
  root=Path(tmp)
  for name,path,digest in [('source',r['source_archive'],r['source_archive_sha256']),('data',r['input_archive'],r['input_archive_sha256'])]:
   require(sha(path)==digest,'archive hash');(root/name).mkdir()
   with tarfile.open(path) as t:t.extractall(root/name,filter='data')
  ass=dict(experiment='E79',gpu_count=1,pod_id='CPU_STUB',pod_created_epoch=time.time(),prior_seconds=0,cap_seconds=r['cap_seconds'],daily_budget_verified=True,projected_daily_USD=260);ass['custody_start_epoch']=ass['pod_created_epoch'];ass['absolute_deadline_epoch']=ass['pod_created_epoch']+ass['cap_seconds'];dump(root/'assignment.json',ass);dump(root/'assets.json',{})
  args=[sys.executable,str(root/'source/results/g_agreement/understand/e79/worker.py'),'--inputs',str(root/'data/inputs'),'--assignment',str(root/'assignment.json'),'--assets',str(root/'assets.json'),'--out',str(root/'out'),'--source-sha',r['source_seal_sha256'],'--input-sha',r['input_seal_sha256'],'--dry-run'];v=subprocess.run(args,capture_output=True,text=True);require(v.returncode==0,v.stderr);proof=read(root/'out/DRY_RUN.json');require(proof['status']=='PASS','full dry run')
  ass['cap_seconds']+=1;ass['absolute_deadline_epoch']+=1;atomic(root/'assignment.json',ass);args[args.index('--out')+1]=str(root/'badcap');v=subprocess.run(args,capture_output=True,text=True);require(v.returncode!=0 and 'stage request cap' in v.stderr,'excess cap rejected')
  (root/'data/inputs/vectors.npy').unlink();args[args.index('--out')+1]=str(root/'missing');v=subprocess.run(args,capture_output=True,text=True);require(v.returncode!=0,'missing vector seal rejected')
 atomic(HERE/'EXACT_PREFLIGHT.json',dict(proof,source_archive_sha256=r['source_archive_sha256'],input_archive_sha256=r['input_archive_sha256'],overcap_rejected=True,missing_input_rejected=True))
 print('EXACT_ARCHIVE_PASS')
if __name__=='__main__':run()
