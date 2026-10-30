"""Build label-free shard-local packets from verified first-wave capture binding; no reader text."""
import argparse,shutil,tarfile,copy,hashlib,json
from worker import *
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def build(e,shards,root):
 binding=read(HERE.parent/'joint9/INPUT_BINDING.json');old=Path(binding['inputs']);verify(old,'INPUT_SEAL.json',binding['input_seal_sha256']);parent=read(old/'PLAN.json')
 for sh in shards:
  out=root/(e+'_'+str(sh));out.mkdir(parents=True,exist_ok=False);(out/'packets').mkdir()
  jobs=[];pilots=[]
  for orig in parent['jobs']:
   if orig['exp']!=e or (not orig['retained_pilot'] and orig['shard']!=sh):continue
   displays=['D4','D3'] if e=='E61' else [e]
   for stage in displays:
    ix=[i for i,x in enumerate(orig['units']) if e!='E61' or x.get('display')==stage]
    if not ix:continue
    key=orig['key']+':'+stage
    if orig['retained_pilot']:
     # One owner for each retained record; no pilot data reaches a pod.
     if sh==0:pilots.append({'original_key':orig['key'],'indices':ix,'stage':stage,'key':key,'reader':orig['reader'],'kind':orig['kind']})
     continue
    j=copy.deepcopy(orig);j.update(key=key,original_key=orig['key'],indices=ix,stage=stage,number=len(jobs));j['units']=[orig['units'][i] for i in ix]
    if orig['h_file']:
     arr=np.load(old/orig['h_file']);j['h_file']='packets/'+str(len(jobs))+'.npy';np.save(out/j['h_file'],arr[ix])
    # Keep full measured batch duration for smaller split batches (conservative).
    jobs.append(j)
  caps={'E61':[6292]*3,'E57':[7207,7206,7206],'E56':[5949,5948,5948]}
  plan={'authority':'402be5f0','cohort_id':COHORT,'experiment':e,'shard':sh,'compute_cap_seconds':caps[e][sh],'jobs':jobs,'retained_pilots':pilots,'capture_seals':parent['capture_seals'][e],'parent_plan_sha256':parent['identity'],'parent_input_seal_sha256':binding['input_seal_sha256']}
  write(out/'PLAN.json',plan);shutil.copytree(old/'parity',out/'parity');seal(out,'INPUT_SEAL.json',{'experiment':e,'shard':sh,'cohort_id':COHORT,'label_free':True})
  archive=out.with_suffix('.tar.gz')
  with tarfile.open(archive,'w:gz',compresslevel=1) as t:t.add(out,arcname='inputs')
  write(HERE/(e+'_'+str(sh)+'_BINDING.json'),{'inputs':str(out),'archive':str(archive),'archive_sha256':sha(archive),'input_seal_sha256':sha(out/'INPUT_SEAL.json'),'plan_sha256':sha(out/'PLAN.json'),'compute_cap_seconds':caps[e][sh],'jobs':len(jobs),'retained_pilots':len(pilots)})
  print(e,sh,len(jobs),archive.stat().st_size,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--experiment',required=True);p.add_argument('--shards',nargs='+',type=int,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.experiment,a.shards,a.out)
