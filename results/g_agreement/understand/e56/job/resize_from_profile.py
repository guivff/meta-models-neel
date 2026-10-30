"""CPU timing proposal from integrator-verified real GPU timings; never invent timings."""
import argparse,math
from pathlib import Path
from contract56 import read,dump,verify,sha,require

def allocation(forecast,setup,registered):
 require(forecast>0 and 0<=setup<=900,'finite positive forecast and bounded setup')
 requested=math.ceil(max(1.5*forecast+360,2*forecast+setup))
 require(requested<=2*registered,'NO_FIT exceeds section149 twice-current ceiling')
 return requested

def main():
 p=argparse.ArgumentParser()
 for k in ('profile','receipt','workload','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();r=read(a.receipt);require(r['verified'] is True,'integrator-verified profile');s=verify(a.profile,'PROFILE_SEAL.json',r['profile_seal_sha256']);require(s['pod_id']==r['pod_id'],'profile custody')
 v=read(a.profile/'PROFILE.json');require(v['real_GPU_job'] is True and v['batch_items']==8 and v['readouts_per_item']==1,'real single-readout job')
 times={k:max(xs) for k,xs in v['phase_seconds'].items()};result={}
 for stage,w in read(a.workload).items():
  forecast=sum(times[k]*n for k,n in w['phase_jobs'].items());setup=sum(times[k]*n for k,n in w['setup_loads'].items())
  result[stage]={'forecast_seconds':forecast,'setup_seconds':setup,'cap_seconds':allocation(forecast,setup,w['registered_cap_seconds'])}
 dump(a.out,{'profile_seal_sha256':sha(a.profile/'PROFILE_SEAL.json'),'workload_sha256':sha(a.workload),'allocations':result,'status':'MEASURED_CAP_PROPOSAL_REQUIRES_COMMITTED_REQUEST'})
if __name__=='__main__':main()
