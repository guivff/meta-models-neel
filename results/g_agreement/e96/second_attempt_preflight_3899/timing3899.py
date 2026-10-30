"""§204 deviation3 operational timing: measured setup and steady work, no new samples."""
import math,hashlib,json
from pathlib import Path
PHASES=('generate_oracle','generate_nla','reconstruct_oracle','reconstruct_nla')
MARGIN=1.25

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def derive(profiles,plan,original_sample_sha256,staging_measurements):
 if not profiles:raise ValueError('sealed timing profiles required')
 groups=[];sources=[]
 for folder in profiles:
  folder=Path(folder);seal=json.loads((folder/'OUTPUT_SEAL.json').read_text());run=json.loads((folder/'RUN.json').read_text());p=folder/'TIMING.json'
  if seal['status']!='COMPLETE' or run['status']!='COMPLETE' or seal['files']['TIMING.json']!=digest(p):raise ValueError('complete sealed timing profile binding')
  g={}
  for e in json.loads(p.read_text()):
   v=e['seconds']
   if not isinstance(v,(float,int)) or not math.isfinite(v) or v<=0:raise ValueError('positive finite timing')
   g.setdefault(e['phase'],[]).append(v)
  if any(len(g.get(k+'_setup',[]))!=1 or len(g.get(k,[]))<2 for k in PHASES) or len(g.get('verify_assets',[]))!=1:raise ValueError('all phases with setup and steady timings required')
  groups.append(g);sources.append({'slot':run['slot'],'timing_sha256':digest(p),'output_seal_sha256':digest(folder/'OUTPUT_SEAL.json'),'setup_seconds':sum(g[k+'_setup'][0] for k in PHASES)})
 counts={k:sum(row['slot']==1 and k.split('_',1)[1] in row['readers'] for row in plan['rows'])*20 for k in PHASES}
 if (counts['generate_oracle']+counts['generate_nla'])*32!=17920:raise ValueError('exact original slot1 grid')
 phases={k:{'jobs':counts[k],'first_batch_seconds':max(g[k][0] for g in groups),'steady_batch_seconds':max(sum(g[k][1:])/len(g[k][1:]) for g in groups)} for k in PHASES}
 setup=max(x['setup_seconds'] for x in sources);verification=max(g['verify_assets'][0] for g in groups);work=sum(v['first_batch_seconds']+v['steady_batch_seconds']*(v['jobs']-1) for v in phases.values())
 if len(staging_measurements)!=len(profiles) or any(not math.isfinite(v) or v<=0 for v in staging_measurements):raise ValueError('measured staging required')
 staging=math.ceil(MARGIN*max(staging_measurements));retrieval=660
 forecast=MARGIN*(setup+verification+work)+staging+retrieval
 if forecast>14400:raise ValueError('measured padded forecast does not fit registered4hcap')
 return {'authority':'3899e1ea073f8609f33fb35b5ce1863c6223961f','kind':'OPERATIONAL_TIMING_ONLY_NO_READOUT_SELECTION','sources':sources,'max_measured_setup_seconds':setup,'setup_cap_seconds':math.ceil(MARGIN*setup),'margin':MARGIN,'verification_max_seconds':verification,'phases':phases,'measured_work_seconds':work,'measured_staging_seconds':staging_measurements,'staging_allowance_seconds':staging,'custody_retrieval_reserve_seconds':retrieval,'padded_complete_forecast_seconds':forecast,'registered_custody_cap_seconds':14400,'original_sample_sha256':original_sample_sha256,'first_batch_policy':'Retain every first batch unchanged; its cold-start latency is measured separately, never multiplied as steady work; no additional warmup samples or discarded outputs.'}

def remaining(profile,phase,left,observed,setup_spent):
 if phase not in PHASES or left<0 or any(not math.isfinite(x) or x<=0 for x in observed):raise ValueError('valid observed timing/grid required')
 rate=profile['phases'][phase]['steady_batch_seconds']
 if len(observed)>1:rate=max(rate,sum(observed[1:])/len(observed[1:]))
 work=left*rate
 for k in PHASES[PHASES.index(phase)+1:]:
  v=profile['phases'][k];work+=v['first_batch_seconds']+v['steady_batch_seconds']*(v['jobs']-1)
 return profile['margin']*work+max(0,profile['setup_cap_seconds']-setup_spent)

def staging_budget(created,cap,now):
 left=created+cap-now
 if left<=0:raise TimeoutError("original staging cap expired")
 return min(900,left)
