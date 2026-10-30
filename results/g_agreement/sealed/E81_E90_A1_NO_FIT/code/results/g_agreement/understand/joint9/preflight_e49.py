import json,tarfile,tempfile,sys,time,subprocess,hashlib
from pathlib import Path
r=json.loads(Path('results/g_agreement/understand/joint9/E49_STAGE_REQUEST.json').read_text())
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='e49-exact-') as tmp:
 root=Path(tmp)
 for key,path,digest in [('source',r['source_archive'],r['source_archive_sha256']),('data',r['input_archive']['path'],r['input_archive']['sha256'])]:
  assert h(path)==digest;(root/key).mkdir()
  with tarfile.open(path) as t:t.extractall(root/key,filter='data')
 items=json.loads((root/'data/inputs/items.json').read_text());assert len(items)==672 and all(set(x)=={'id','feature'} for x in items)
 a=dict(r['assignment_schema'],absolute_deadline_epoch=time.time()+1800,pod_id='CPU_STUB');(root/'assignment.json').write_text(json.dumps(a));(root/'assets.json').write_text('{}')
 script='''import sys,runpy
from pathlib import Path
root=Path(sys.argv[1]);job=root/'source/results/g_agreement/understand/e49/nla_supplement';sys.path.insert(0,str(job));import prepare,worker56,native_nla512
class Stub:
 def __init__(self,*a,**k):self.nla=object()
 def load_nla(self):pass
worker56.Backend=Stub
native_nla512.native_nla=lambda model,h,k:[[{'text':'CPU STUB </explanation>','raw':'CPU STUB </explanation>','truncated':False}] for _ in h]
sys.argv=['worker.py','--inputs',str(root/'data/inputs'),'--assets',str(root/'assets.json'),'--assignment',str(root/'assignment.json'),'--out',str(root/'out')]
runpy.run_path(str(job/'worker.py'),run_name='__main__')
'''
 p=subprocess.run([sys.executable,'-c',script,str(root)],capture_output=True,text=True)
 if p.returncode:raise RuntimeError(p.stderr)
 assert json.loads((root/'out/OUTPUT_SEAL.json').read_text())['status']=='COMPLETE'
Path('results/g_agreement/understand/joint9/E49_PREFLIGHT.json').write_text(json.dumps({'status':'PASS','GPU_calls':0,'items':672,'label_free':True,'full_worker_path_stubbed':True,'source_archive_sha256':r['source_archive_sha256'],'input_archive_sha256':r['input_archive']['sha256']},indent=2)+'\n')
print('E49_EXACT_ARCHIVE_STUB_PASS')
