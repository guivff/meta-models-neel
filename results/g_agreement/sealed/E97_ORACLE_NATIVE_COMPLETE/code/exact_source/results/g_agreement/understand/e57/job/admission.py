"""Operational admission only: retained pilot jobs, bounded custody, durable forecasts."""
import time,json,os,math
from collections import Counter
from contract56 import read,require
class NoFit(RuntimeError):pass

def atomic(path,value):
 tmp=path.with_suffix(path.suffix+'.tmp')
 with tmp.open('w') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def validate_allocation(a):
 registered={'E56':9000,'E57':5400,'E61':1800};slot=a['slot'];require(slot in (0,1,2) and a['gpu_count']==1,'single GPU shard')
 caps={}
 for e,alloc in a['allocation_by_slot'].items():
  require(e in registered and set(alloc)==({'0'} if e=='E61' else {'0','1','2'}),'registered experiment slots')
  require(all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in alloc.values()),'finite positive caps')
  prior=a['prior_custody_seconds'][e];require(prior>=0 and sum(alloc.values())+prior<=2*registered[e],'twice registered total includes prior custody')
  if str(slot) in alloc:caps[e]=alloc[str(slot)]
 require(set(caps)==({'E56','E57','E61'} if slot==0 else {'E56','E57'}),'shard experiments')
 end=a['pod_created_epoch']+sum(caps.values());require(a['absolute_deadline_epoch']==end,'creation-based joint deadline')
 return caps,end

class Budget:
 def __init__(self,out,caps,end,seed):
  self.out=out;self.caps=caps;self.end=end;self.seed=seed;self.cost={};self.observed={};self.events=[]
 def check(self):
  if time.time()>=self.end-60:raise NoFit('retrieval reserve')
 def call(self,key,fn,experiment=None):
  self.check();start=time.monotonic()
  try:value=fn()
  except BaseException:
   self.events.append({'phase':key,'status':'FAILED','seconds':time.monotonic()-start});atomic(self.out/'PHASE_TIMINGS.json',self.events);raise
  elapsed=time.monotonic()-start;self.observed.setdefault(key,[]).append(elapsed)
  if experiment:self.cost[experiment]=self.cost.get(experiment,0)+elapsed
  self.events.append({'phase':key,'status':'COMPLETE','experiment':experiment,'seconds':elapsed});atomic(self.out/'PHASE_TIMINGS.json',self.events);self.check();return value
 def forecast(self,jobs,results,reload_oracle):
  remaining=Counter((j['exp'],j['phase']) for i,j in enumerate(jobs) if i not in results);unknown=sorted({k for _,k in remaining if k not in self.observed})
  setup=max(self.seed['oracle_setup'],max(self.observed.get('oracle_setup',[0]))) if reload_oracle else 0
  forecasts={e:0. for e in self.caps}
  for (e,key),count in remaining.items():
   if key not in self.observed:continue
   per=max(self.observed[key]);per=max(per,self.seed['oracle_native_8_items']) if key.endswith('oracle_native') else per
   forecasts[e]+=2*count*per
  shared=max(0,time.time()-(self.end-sum(self.caps.values()))-sum(self.cost.values()))+2*setup+60
  charged={e:self.cost.get(e,0)+shared*self.caps[e]/sum(self.caps.values())+forecasts[e] for e in self.caps}
  fits=not unknown and all(charged[e]<=self.caps[e] for e in charged) and time.time()+sum(forecasts.values())+2*setup+60<self.end
  result={'status':'ADMIT' if fits else 'NO_FIT','remaining_jobs':{'|'.join(k):v for k,v in remaining.items()},'unknown_phases':unknown,'remaining_forecast_seconds':sum(forecasts.values())+2*setup,'charged_forecast_by_experiment':charged,'caps':self.caps,'deadline_epoch':self.end,'recorded_epoch':time.time(),'completed_jobs':len(results),'pilot_outputs_retained':True,'margin':2.0}
  atomic(self.out/'FORECAST.json',result)
  if not fits:raise NoFit('full-run forecast does not fit')
  return result

def admit_and_run(jobs,backend,budget,execute):
 results={}
 # Pilot first two jobs of EVERY phase, without recomputation. Forecast sees both readers before admission.
 for reader in ('oracle','nla'):
  if reader=='nla':budget.call('nla_setup',backend.load_nla)
  seen=Counter()
  for i,j in enumerate(jobs):
   if j['reader']!=reader or seen[j['phase']]>=2:continue
   results[i]=budget.call(j['phase'],lambda j=j:execute(j),j['exp']);seen[j['phase']]+=1
  atomic(budget.out/'PILOT_RESULTS.json',{str(i):v for i,v in results.items()})
 budget.forecast(jobs,results,any(j['reader']=='oracle' and i not in results for i,j in enumerate(jobs)))
 # NLA is resident after pilots. Finish it first; then reload Oracle only once if needed.
 for reader in ('nla','oracle'):
  pending=[i for i,j in enumerate(jobs) if j['reader']==reader and i not in results]
  if reader=='oracle' and pending:
   backend.nla=None
   import gc,torch
   gc.collect();torch.cuda.empty_cache();budget.call('oracle_setup',backend.load_oracle)
  for i in pending:
   j=jobs[i];results[i]=budget.call(j['phase'],lambda j=j:execute(j),j['exp'])
   budget.forecast(jobs,results,reader=='nla' and any(x['reader']=='oracle' and k not in results for k,x in enumerate(jobs)))
 return results
