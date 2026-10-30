"""Bind a frozen public bank into disjoint, exact-tested shard archives."""
import argparse,tarfile,tempfile,subprocess,json,hashlib,time,shutil
from pathlib import Path
from worker import *

def pack(e,bank,bank_sha,dest,nshards=1,prior=0):
 verify(bank,'INPUT_SEAL.json',bank_sha);items=read(bank/'items.json');validate_items(e,items,full=True)
 require(type(nshards)is int and 1<=nshards<=3 and 0<=prior<CAPS[e],'shard budget')
 dest.mkdir(parents=True,exist_ok=False);total=CAPS[e]-prior;caps=[total//nshards+(i<total%nshards) for i in range(nshards)]
 source=HERE/'SOURCE_SEAL.json';verify(HERE,'SOURCE_SEAL.json');deps=read(HERE/'DEPENDENCIES.json');arc=dest/'source.tar.gz'
 names=set(deps)|{str((HERE/n).relative_to(ROOT)) for n in read(source)['files']}|{str(source.relative_to(ROOT))}
 with tarfile.open(arc,'w:gz') as t:
  for n in sorted(names):t.add(ROOT/n,arcname=n)
 keys=sorted({x.get('base_item_id',x['id']) for x in items});assignment={k:i%nshards for i,k in enumerate(keys)}
 req=dict(experiment=e,status='PREFLIGHT_PENDING',launch_allowed=False,authority='8b2012d7 sections185-189; user priority',source_archive=str(arc),source_archive_sha256=sha(arc),source_seal_sha256=sha(source),bank_seal_sha256=bank_sha,registered_total_seconds=CAPS[e],prior_seconds=prior,forecast_required=False,compute_clock='provider creation, setup included',upload_parallel=True,shards=[])
 vectors=np.load(bank/'vectors.npy',allow_pickle=False) if e=='E70' else None
 if vectors is not None:require(vectors.shape==(len(items),5120) and vectors.dtype==np.float32 and np.isfinite(vectors).all(),'supplier vector grid')
 for slot in range(nshards):
  ix=[i for i,x in enumerate(items) if assignment[x.get('base_item_id',x['id'])]==slot];xs=[items[i] for i in ix];require(xs,'nonempty shard');inp=dest/f'shard_{slot}'/'inputs';inp.mkdir(parents=True)
  dump(inp/'items.json',xs)
  if vectors is not None:np.save(inp/'vectors.npy',vectors[ix])
  plan=dict(experiment=e,shard=slot,cap_seconds=caps[slot],all_shard_caps=caps,prior_seconds=prior,forecast_required=False,bank_seal_sha256=bank_sha,item_ids=[x['id'] for x in xs]);dump(inp/'PLAN.json',plan);seal(inp,'INPUT_SEAL.json',dict(experiment=e,bank_seal_sha256=bank_sha,shard=slot))
  archive=dest/f'shard_{slot}.tar.gz'
  with tarfile.open(archive,'w:gz') as t:t.add(inp,arcname='inputs')
  req['shards'].append(dict(shard=slot,input_archive=str(archive),input_archive_sha256=sha(archive),input_seal_sha256=sha(inp/'INPUT_SEAL.json'),item_ids=plan['item_ids'],assignment_schema=dict(experiment=e,shard=slot,gpu_count=1,cap_seconds=caps[slot],pod_id='INTEGRATOR',pod_created_epoch='PROVIDER_CREATION',absolute_deadline_epoch='pod_created_epoch + cap_seconds',daily_budget_verified=True,projected_daily_USD='INTEGRATOR_VERIFIED')))
 request=dest/'REQUEST.json';dump(request,req);exact_preflight(request)
 req.update(status='READY',launch_allowed=True,worker_argv=['python','results/g_agreement/understand/e68_runner/worker.py','--inputs','SHARD_INPUTS','--assignment','ASSIGNMENT','--assets','ASSETS','--out','NEW_EXCLUSIVE_OUTPUT','--source-sha',req['source_seal_sha256'],'--input-sha','SHARD_INPUT_SEAL_SHA256']);atomic(request,req);return request

def exact_preflight(request):
 r=read(request);proof=[]
 for s in r['shards']:
  with tempfile.TemporaryDirectory(prefix='late185-exact-') as tmp:
   root=Path(tmp)
   for name,path,digest in [('source',r['source_archive'],r['source_archive_sha256']),('data',s['input_archive'],s['input_archive_sha256'])]:
    require(sha(path)==digest,'exact archive');(root/name).mkdir()
    with tarfile.open(path) as t:t.extractall(root/name,filter='data')
   a=dict(s['assignment_schema'],pod_id='CPU_STUB',pod_created_epoch=time.time(),projected_daily_USD=100);a['absolute_deadline_epoch']=a['pod_created_epoch']+a['cap_seconds'];dump(root/'assignment.json',a);dump(root/'assets.json',{})
   args=[sys.executable,str(root/'source/results/g_agreement/understand/e68_runner/worker.py'),'--inputs',str(root/'data/inputs'),'--assignment',str(root/'assignment.json'),'--assets',str(root/'assets.json'),'--out',str(root/'out'),'--source-sha',r['source_seal_sha256'],'--input-sha',s['input_seal_sha256'],'--dry-run']
   result=subprocess.run(args,capture_output=True,text=True);require(result.returncode==0,result.stderr);proof.append(read(root/'out/DRY_RUN.json'))
   (root/'data/inputs/PLAN.json').unlink();args[args.index('--out')+1]=str(root/'negative');result=subprocess.run(args,capture_output=True,text=True);require(result.returncode!=0,'missing sealed input rejected')
 dump(request.with_name('EXACT_PREFLIGHT.json'),dict(status='PASS',shards=proof,missing_plan_rejected=True,source_archive_sha256=r['source_archive_sha256'],input_archives_sha256=[s['input_archive_sha256'] for s in r['shards']],production_GPU_calls=0))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--experiment',choices=CAPS,required=True);p.add_argument('--bank',type=Path,required=True);p.add_argument('--bank-sha',required=True);p.add_argument('--dest',type=Path,required=True);p.add_argument('--shards',type=int,default=1);p.add_argument('--prior-seconds',type=int,default=0);a=p.parse_args();print(pack(a.experiment,a.bank,a.bank_sha,a.dest,a.shards,a.prior_seconds))
