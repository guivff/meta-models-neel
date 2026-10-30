"""Extract exact production source and sealed captures; execute NLA on tiny CPU model."""
import sys,tarfile,tempfile,subprocess,time,json
from pathlib import Path
from prepare import HERE
from contract56 import read,dump,sha,require

def run(request):
 r=read(request)
 with tempfile.TemporaryDirectory(prefix='e49-nla-exact-') as tmp:
  root=Path(tmp)
  for name,path,digest in [('source',r['source_archive'],r['source_archive_sha256']),('data',r['input_archive']['path'],r['input_archive']['sha256'])]:
   require(sha(path)==digest,'exact archive');(root/name).mkdir()
   with tarfile.open(path) as t:t.extractall(root/name,filter='data')
  a=dict(r['assignment_schema'],pod_id='CPU_STUB',pod_created_epoch=time.time(),existing_pod=False,projected_daily_USD=100);a['custody_started_epoch']=a['pod_created_epoch'];a['absolute_deadline_epoch']=a['pod_created_epoch']+a['cap_seconds'];dump(root/'assignment.json',a);dump(root/'assets.json',{})
  args=[sys.executable,str(root/'source/results/g_agreement/understand/e49/nla_supplement/worker.py'),'--inputs',str(root/'data/inputs'),'--assets',str(root/'assets.json'),'--assignment',str(root/'assignment.json'),'--out',str(root/'out'),'--dry-run'];result=subprocess.run(args,capture_output=True,text=True);require(result.returncode==0,result.stderr);proof=read(root/'out/DRY_RUN.json')
  (root/'data/inputs/acts42.npy').unlink();args[args.index('--out')+1]=str(root/'negative');result=subprocess.run(args,capture_output=True,text=True);require(result.returncode!=0,'missing sealed capture rejected')
 report=dict(proof,source_archive_sha256=r['source_archive_sha256'],input_archive_sha256=r['input_archive']['sha256'],missing_capture_rejected=True);request.with_name('EXACT_PREFLIGHT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');return report
if __name__=='__main__':print(run(Path(sys.argv[1])))
