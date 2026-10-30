"""Freeze job ownership from first-wave timing journals without opening reader payloads."""
import argparse,shutil,tarfile,hashlib
from types import SimpleNamespace
from collections import Counter
from runtime import *

def prepare(out):
 out.mkdir(parents=True,exist_ok=False);pull=ROOT/'cache/g_agreement/understand/e56_e57/verified_pull_single_v1';times=ROOT/'cache/g_agreement/understand/e56_e57/first_wave_nofit_timings_v1';bindings={e:read(HERE.parent/e.lower()/'job/INPUT_BINDING.json') for e in CAPS};assets=out/'CPU_ASSETS.json';dump(assets,{})
 plan={'authority':'32c55cb7','caps':CAPS,'jobs':[],'capture_seals':{e:{} for e in CAPS},'timing_sources':{},'pilot_payloads':'retained in integrator custody; excluded here; mandatory at final exact-union assembly'};packet=out/'packets';packet.mkdir()
 for slot in range(3):
  old=pull/f'shard_{slot}/out';a=SimpleNamespace(assignment=old/'e56/ASSIGNMENT.json',e56_inputs=Path(bindings['E56']['inputs']),e57_inputs=Path(bindings['E57']['inputs']),e61_inputs=Path(bindings['E61']['inputs']) if slot==0 else None,assets=assets)
  ass,caps,end,states,parity=old_preflight(a);ready=read(old/'CAPTURE_READY.json');journal=times/f'shard_{slot}/PHASE_TIMINGS.json';forecast=read(times/f'shard_{slot}/FORECAST.json');require(forecast['status']=='NO_FIT' and forecast['pilot_outputs_retained'] is True,'preserved pilot stop')
  counts=Counter(x['phase'] for x in read(journal) if x['status']=='COMPLETE');plan['timing_sources'][str(slot)]={'path':str(journal),'sha256':sha(journal),'forecast_sha256':sha(times/f'shard_{slot}/FORECAST.json')}
  for e,s in states.items():
   cap=old/e.lower()/'capture';verify(cap,'CAPTURE_SEAL.json',ready['capture_seals'][e]);target=out/'captures'/e/str(slot);shutil.copytree(cap,target);plan['capture_seals'][e][str(slot)]=sha(cap/'CAPTURE_SEAL.json')
   order=read(cap/('POSITION_ORDER.json' if e=='E61' else 'items.order.json'));require(order==(s['capture_items'] if e=='E61' else [x['id'] for x in s['capture_items']]),'original order')
   s['acts']={l:np.load(cap/f'acts{l}.npy',mmap_mode='r') for l in (42,44)};s['index']={x['id']:i for i,x in enumerate(s['capture_items'])}
  jobs=make_jobs(states,slot);seen=Counter();pilots=0
  for j in jobs:
   phase=j['phase'];seen[phase]+=1;is_pilot=seen[phase]<=min(2,counts[phase]);require(counts[phase]==min(2,sum(x['phase']==phase for x in jobs)),'only original first-two pilots completed')
   pilots+=is_pilot;key=f'{slot}:{j["number"]}';name=f'packets/{slot}_{j["number"]}.npy' if j['h'] is not None else None
   if name:np.save(out/name,j['h'])
   j['units']=[{k:v for k,v in x.items() if k not in ('label','value','class')} for x in j['units']]
   plan['jobs'].append({k:v for k,v in j.items() if k not in ('h','number')}|{'key':key,'source_slot':slot,'source_job_number':j['number'],'retained_pilot':is_pilot,'h_file':name,'measured_seconds':max(forecast['observed'][phase])})
  require(pilots==forecast['completed_jobs'],'pilot job count matches measured forecast')
 for e in CAPS:
  loads=[0.,0.,0.]
  for j in sorted([x for x in plan['jobs'] if x['exp']==e and not x['retained_pilot']],key=lambda x:(-x['measured_seconds'],x['key'])):
   shard=min(range(3),key=lambda i:(loads[i],i));j['shard']=shard;loads[shard]+=j['measured_seconds']
  for j in plan['jobs']:
   if j['exp']==e and j['retained_pilot']:j['shard']=None
  print(e,'unfinished job seconds per shard',loads)
 for i,j in enumerate(plan['jobs']):j['resume_number']=i
 dump(out/'PLAN_BODY.json',plan);plan['identity']=sha(out/'PLAN_BODY.json');dump(out/'PLAN.json',plan);shutil.copytree(Path(bindings['E56']['inputs'])/'parity',out/'parity');assets.unlink()
 dump(out/'INPUT_SEAL.json',{'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()},'status':'SEALED_RESUME_INPUTS','plan_sha256':plan['identity']})
 archive=out.with_suffix('.tar.gz')
 with tarfile.open(archive,'w:gz',compresslevel=1) as t:t.add(out,arcname='inputs')
 dump(HERE/'INPUT_BINDING.json',{'inputs':str(out),'input_seal_sha256':sha(out/'INPUT_SEAL.json'),'archive':str(archive),'archive_sha256':sha(archive),'plan_sha256':plan['identity'],'capture_seals':plan['capture_seals'],'retained_pilot_jobs':sum(x['retained_pilot'] for x in plan['jobs']),'unfinished_jobs':sum(not x['retained_pilot'] for x in plan['jobs'])})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
