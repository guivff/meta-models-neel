import json,sys,tempfile,tarfile,subprocess,time,argparse,hashlib
from pathlib import Path
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(request):
 r=json.loads(request.read_text());proof=[]
 for sh in r['shards']:
  with tempfile.TemporaryDirectory(prefix='402-exact-') as tmp:
   root=Path(tmp)
   for name,path,digest in [('source',r['source_archive'],r['source_archive_sha256']),('data',sh['input_archive'],sh['input_archive_sha256'])]:
    assert h(path)==digest;(root/name).mkdir()
    with tarfile.open(path) as t:t.extractall(root/name,filter='data')
   ass=dict(sh['assignment_schema'],pod_id='CPU_STUB',pod_created_epoch=time.time(),daily_budget_verified=True,projected_daily_USD=100);ass['dependency_receipt']={'verified':True,'cohort_id':r['cohort_id'],'E57_output_seals':['a'*64]*3,'E61_D4_stage_seals':['b'*64]*3};ass['staging_start_epoch']=ass['pod_created_epoch'];ass['absolute_deadline_epoch']=ass['staging_start_epoch']+900+ass.get('go_wait_cap_seconds',0)+ass['compute_cap_seconds'];(root/'assignment.json').write_text(json.dumps(ass));(root/'assets.json').write_text('{}')
   args=[sys.executable,str(root/'source/results/g_agreement/understand/follow402/worker.py'),'--inputs',str(root/'data/inputs'),'--assignment',str(root/'assignment.json'),'--assets',str(root/'assets.json'),'--out',str(root/'out'),'--go',str(root/'GO.json'),'--source-sha',r['source_seal_sha256'],'--input-sha',sh['input_seal_sha256'],'--dry-run'];p=subprocess.run(args,capture_output=True,text=True)
   if p.returncode:raise RuntimeError(p.stderr)
   proof.append(json.loads((root/'out/DRY_RUN.json').read_text()));(root/'data/inputs/parity/INPUT_SEAL.json').unlink();args[args.index('--out')+1]=str(root/'negative');p=subprocess.run(args,capture_output=True,text=True);assert p.returncode and 'INPUT_SEAL.json' in p.stderr
 report={'status':'PASS','shards':proof,'missing_parity_seal':'REJECTED_EACH_SHARD','source_archive_sha256':r['source_archive_sha256'],'input_archives':{x['experiment']+'_'+str(x['shard']):x['input_archive_sha256'] for x in r['shards']},'GPU_calls':0};request.with_name(request.stem+'_PREFLIGHT.json').write_text(json.dumps(report,indent=2)+'\n');print('EXACT_ARCHIVE_PASS',len(proof))
if __name__=='__main__':run(Path(sys.argv[1]))
