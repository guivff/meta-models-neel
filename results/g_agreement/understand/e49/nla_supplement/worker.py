"""Descriptive E49 NLA supplement. Never opens or rewrites original outputs."""
import argparse,sys,time,threading,os,signal,json,math
from pathlib import Path
import numpy as np
from prepare import HERE,ROOT,E56
from contract56 import read,dump,verify,sha,seal,require
from worker56 import Backend
from native_nla512 import native_nla,truncation_summary

def warmup(nla):
 # No real capture or item is an input to this function.
 native_nla(nla,np.random.default_rng(20261028).standard_normal((8,5120)).astype(np.float32),k=1)

def custody(ass,now):
 require(ass['gpu_count']==1,'one GPU')
 forecast=ass['measured_forecast_seconds'];cap=ass['cap_seconds']
 require(type(forecast) in (int,float) and math.isfinite(forecast) and forecast>0,'positive measured forecast')
 require(cap==read(HERE/'CAP_LIMITS.json')['cap_seconds'],'sealed stage request cap')
 require(ass['daily_budget_verified'] is True and 0<=ass['projected_daily_USD']<=260,'Track Q USD260 projected account gate; USD100 reserved for I-2 within USD500 day ceiling')
 origin=ass['custody_started_epoch'] if ass['existing_pod'] else ass['pod_created_epoch']
 require(math.isfinite(origin) and origin<=now and ass['absolute_deadline_epoch']==origin+cap,'fixed custody deadline including setup')
 require(now<origin+cap-60,'custody reserve')
 return origin+cap

def main():
 p=argparse.ArgumentParser()
 for key in ('inputs','assets','assignment','out'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--dry-run',action='store_true');a=p.parse_args();ass=read(a.assignment);start=time.time();end=custody(ass,start)
 forecast=read(HERE/'MEASURED_FORECAST.json');require(forecast['status']=='MEASURED' and forecast['forecast_seconds']==ass['measured_forecast_seconds'] and sha(HERE/'MEASURED_FORECAST.json')==ass['forecast_sha256'],'committed measured forecast')
 verify(HERE,'SOURCE_SEAL.json',ass['source_seal_sha256']);verify(a.inputs,'INPUT_SEAL.json',ass['input_seal_sha256'])
 for path,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/path)==digest,'dependency pin')
 items=read(a.inputs/'items.json');h=np.load(a.inputs/'acts42.npy',allow_pickle=False);require(h.shape==(672,5120) and np.isfinite(h).all() and len(items)==672 and len({x['id'] for x in items})==672 and all(set(x)=={'id','feature'} for x in items),'sealed label-free same672 capture grid')
 a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'ASSIGNMENT.json',dict(ass,stage_started_epoch=start));timer=threading.Timer(end-start,lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 events=[]
 def timing(phase,t):
  events.append({'phase':phase,'seconds':time.monotonic()-t})
  temp=a.out/'PHASE_TIMINGS.tmp';temp.write_text(json.dumps(events,indent=2)+'\n');temp.replace(a.out/'PHASE_TIMINGS.json')
 try:
  t=time.monotonic()
  if a.dry_run:
   from smoke_profile import TinyBackend
   backend=TinyBackend()
  else:backend=Backend(ROOT,a.assets,{'gpu_type':'H200'})
  backend.load_nla();timing('nla_setup',t)
  require(time.time()<end-60,'before warm-up stage cap');t=time.monotonic();warmup(backend.nla);timing('nla_warmup_discarded',t)
  require(time.time()<end-60,'warm-up charged to stage clock');records=[];real_seconds=[];(a.out/'jobs').mkdir()
  for offset in range(0,672,8):
   require(time.time()<end-60,'stage cap');t=time.monotonic();values=native_nla(backend.nla,h[offset:offset+8],k=1);real_seconds.append(time.monotonic()-t);timing('nla_native',t)
   require(len(values)==len(items[offset:offset+8]) and all(len(v)==1 for v in values),'single readout grid')
   batch=[dict(item,**v[0]) for item,v in zip(items[offset:offset+8],values)];dump(a.out/'jobs'/f'{offset:04d}.json',batch);records.extend(batch)
   fits=time.time()+1.25*(sum(real_seconds)/len(real_seconds))*((672-offset-8)//8)<end-60
   (a.out/'FORECAST.json').write_text(json.dumps({'status':'ADMIT' if fits else 'NO_FIT','observed_batch_mean_seconds':sum(real_seconds)/len(real_seconds),'real_batches':len(real_seconds),'remaining_batches':(672-offset-8)//8,'margin':1.25,'deadline_epoch':end,'retained_readouts':len(records)})+'\n')
   if not fits:
    dump(a.out/'NO_FIT.json',{'status':'NO_FIT','retained_readouts':len(records),'remaining_batches':(672-offset-8)//8});return
  with (a.out/'nla_native.jsonl').open('x') as f:
   for x in records:f.write(json.dumps(x,allow_nan=False)+'\n')
  dump(a.out/'NLA_TRUNCATION.json',truncation_summary(records));dump(a.out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':end})
  if a.dry_run:dump(a.out/'DRY_RUN.json',{'status':'PASS','items':len(records),'model_loading':'stubbed','production_GPU_calls':0})
  seal(a.out,'OUTPUT_SEAL.json',{'experiment':'E49_NLA_SUPPLEMENT','status':'COMPLETE','descriptive_only':True,'source_seal_sha256':ass['source_seal_sha256'],'input_seal_sha256':ass['input_seal_sha256'],'pod_id':ass['pod_id']})
 except BaseException as error:dump(a.out/'FAILURE.json',{'error':str(error)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
