"""Extract exact production archives, run real preflight and every stub stage on CPU."""
import argparse,hashlib,json,subprocess,sys,tarfile,tempfile,time
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--request',type=Path,required=True);p.add_argument('--report',type=Path,required=True);a=p.parse_args();r=json.loads(a.request.read_text())
 archives={'source':{'path':r['source_archive'],'sha256':r['source_archive_sha256']},'e56':r['E56_input_archive'],'e57':r['E57_bank_archive'],'e61':r['E61_input_archive']}
 proofs=[]
 with tempfile.TemporaryDirectory(prefix='joint-exact-') as temp:
  root=Path(temp)
  for name,entry in archives.items():
   assert sha(entry['path'])==entry['sha256'],'archive hash mismatch'
   target=root/name;target.mkdir()
   with tarfile.open(entry['path']) as t:t.extractall(target,filter='data')
  source=root/'source';assets=root/'assets.json';assets.write_text('{}')
  for shard in r['shards']:
   slot=shard['slot'];now=time.time();alloc={'E56':{'0':5000,'1':5000,'2':5000},'E57':{'0':3000,'1':3000,'2':3000},'E61':{'0':3000}}
   ass=dict(shard['assignment_schema'],pod_id='CPU_STUB',pod_created_epoch=now,allocation_by_slot=alloc,prior_custody_seconds={'E56':1000,'E57':0,'E61':0},absolute_deadline_epoch=now+sum(v.get(str(slot),0) for v in alloc.values()))
   path=root/f'assignment{slot}.json';path.write_text(json.dumps(ass));out=root/f'out{slot}'
   argv=[sys.executable,str(source/'results/g_agreement/understand/e57/job/production_joint.py'),'--assignment',str(path),'--e56-inputs',str(root/'e56/inputs'),'--e57-inputs',str(root/'e57/inputs'),'--assets',str(assets),'--out',str(out),'--go',str(root/'GO.json'),'--dry-run']
   if slot==0:argv+=['--e61-inputs',str(root/'e61/inputs')]
   result=subprocess.run(argv,cwd=source,capture_output=True,text=True)
   if result.returncode:raise RuntimeError(result.stderr)
   proofs.append(json.loads((out/'DRY_RUN.json').read_text()))
  (root/'e56/inputs/parity/INPUT_SEAL.json').unlink();argv[argv.index('--out')+1]=str(root/'negative')
  result=subprocess.run(argv,cwd=source,capture_output=True,text=True)
  assert result.returncode!=0 and 'INPUT_SEAL.json' in result.stderr,'missing parity seal must fail'
 report={'status':'PASS','source_commit':r['source_commit'],'archive_hashes':{k:v['sha256'] for k,v in archives.items()},'clean_extraction':True,'all_slots':proofs,'missing_parity_seal_regression':'PASS','GPU_calls':0}
 a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print('EXACT_PRODUCTION_ARCHIVES_PASS')
if __name__=='__main__':main()
