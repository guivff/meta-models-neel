"""Exact-union CPU assembly: verified nine-shard outputs plus retained first-wave pilots."""
import argparse
from runtime import *

def assemble(manifest,out):
 m=read(manifest);require(m['verified'] is True,'integrator verified complete custody manifest');inp=Path(m['inputs']);verify(inp,'INPUT_SEAL.json',m['input_seal_sha256']);plan=read(inp/'PLAN.json');results={};sources={}
 for p in m['retained_pilot_pulls']:
  root=Path(p['root']);verify(root,p['seal_file'],p['seal_sha256']);payload=read(root/p['pilot_file']);sources['pilot:'+str(p['slot'])]=p['seal_sha256']
  for n,v in payload.items():
   key=str(p['slot'])+':'+str(n);require(key not in results,'duplicate retained job');results[key]=v
 expected_pilots={j['key'] for j in plan['jobs'] if j['retained_pilot']};require(set(results)==expected_pilots,'all retained pilots exactly once, no replay')
 seen=set()
 for p in m['shards']:
  root=Path(p['root']);s=verify(root,'OUTPUT_SEAL.json',p['output_seal_sha256']);key=(s['experiment'],s['shard']);require(key not in seen and s['status']=='COMPLETE' and s['plan_sha256']==plan['identity'],'unique completed resume shard');seen.add(key)
  ass=read(root/'ASSIGNMENT.json');end=check_assignment(ass,plan);require(read(root/'TIMING.json')['completed_epoch']<end,'shard custody cap');require(read(root/'parity/PARITY_RESULT.json')['status']=='PASS','parity');go=read(root/'GO_RECEIPT.json');require(go['reader_launch_authorized'] is True and go['capture_seals']==plan['capture_seals'][s['experiment']],'standing capture GO')
  jobs=selected_jobs(plan,*key);require(set(read(root/'COMPLETED.json'))=={j['key'] for j in jobs},'complete owned jobs');sources['shard:'+str(key)]=p['output_seal_sha256']
  for j in jobs:
   require(j['key'] not in results,'duplicate or replayed pilot');results[j['key']]=read(root/'jobs'/f'{j["resume_number"]:06d}.json')
 require(seen=={(e,i) for e in CAPS for i in range(3)} and set(results)=={j['key'] for j in plan['jobs']},'nine shards, exact complete original job union')
 # Exclusive assembly directory also prevents silently replacing a previous union.
 out.mkdir(parents=True,exist_ok=False);dump(out/'JOBS.json',results);dump(out/'PLAN.json',plan);seal(out,'ASSEMBLY_SEAL.json',{'status':'COMPLETE_EXACT_UNION','plan_sha256':plan['identity'],'source_custody':sources,'retained_pilot_jobs':len(expected_pilots),'new_jobs':len(results)-len(expected_pilots),'science':'original per-experiment analysis measures/rules unchanged; this step only assembles acquisition'})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assemble(a.manifest,a.out)
