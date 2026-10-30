"""E85 prospective native-only relaunch under the approved cumulative4300s cap, all2474.144266prior retained.
Read retained capture and original CPU release; never capture, fit probes, select,
produce downstream answers, or reuse partial old native readouts. Real parity is
report-only; load/nonfinite/shape/deadline/crash remain fatal. One original clock.
"""
import argparse,time,os,signal,threading,json,hashlib
from pathlib import Path
import numpy as np
import worker as W
from contract import read,write,sha,verify,seal,require
PRIOR=2474.1442658901215
CAPTURE='d77cfa74a8bbc4a2787522e9f72d2594646f771a7f12dc437eddd18283a2a543'
PROBE='8f2b7e3a92b136c9b7c6e671b9673c7ce5a82884fa18107fa77c2c3ddf557533'
RELEASE_RECEIPT='a33984af3a0ed0ba830b8909457a116f8c3c3850d285681742826d200ebdbaa0'

def retained(items,capture,receipt):
 verify(capture,'STAGE_SEAL.json',CAPTURE);require(sha(receipt)==RELEASE_RECEIPT,'immutable original public CPU release');p=read(receipt)
 require(p['experiment']=='E85'and p['capture_seal_sha256']==CAPTURE and p['probe_seal_sha256']==PROBE,'original CPU release lineage')
 allowed=p['released_ids'];require(len(allowed)==len(set(allowed))==400,'original400 released test IDs')
 order=read(capture/'items.order.json');require(len(order)==len(set(order))==len(items)and order==[x['id']for x in items],'original capture ordered public grid')
 positions=read(capture/'POSITIONS.json');require(positions==[dict(id=x['id'],read_index=x['read_index'])for x in items],'all original final read positions')
 ix=[i for i,x in enumerate(items)if x['id']in set(allowed)];units=[items[i]for i in ix]
 require(len(units)==400 and all(x['split']=='test'for x in units),'no dev promotion/new filter')
 # The original public feature/arm are deliberately opaque; CPU-only gate
 # custody binds the2x2groups. Never put those private labels on the pod.
 require(all(x['feature']=='opaque'and x['arm']=='capture'for x in units),'original opaque public metadata')
 acts={}
 for layer in (42,44):
  a=np.load(capture/f'acts{layer}.npy',allow_pickle=False);require(a.shape==(len(items),5120)and np.isfinite(a).all(),'finite retained vectors');acts[layer]=a[ix].copy()
 return units,acts

def report_parity(batched,serial,path,ids):
 require(len(batched)==len(serial)==len(ids)==8,'eight actual parity cells')
 enc=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()
 rows=[dict(id=i,batched_sha256=hashlib.sha256(enc(a)).hexdigest(),serial_sha256=hashlib.sha256(enc(b)).hexdigest(),equal=enc(a)==enc(b))for i,a,b in zip(ids,batched,serial)]
 write(path,dict(status='PASS'if all(x['equal']for x in rows)else'FAIL_REPORT_ONLY',authority='87ee1900',production_batch_size=32,n=8,records=rows))

def run(b,clock,items,acts,out,assignment):
 require(assignment['prior_seconds']>=PRIOR and assignment['prior_seconds']+assignment['cap_seconds']<=4300,'original cumulative custody, no reset')
 b.native_batch_size=32;dummy=np.random.default_rng(0).standard_normal((32,5120)).astype(np.float32)
 profile_path=Path(__file__).with_name('RETAINED_TIMING.json')
 require(sha(profile_path)=='dd1829aba28138a1caaf05b8ea0b21a23aa3958232b651386820a3c6c26fea74','retained original measured timing proof')
 timing=read(profile_path);profile=timing['profile'];work=timing['measured_remaining_work_seconds']
 setup=max(314.85366582870483,time.time()-assignment['custody_start_epoch']);needed=setup+1.25*work+60
 write(out/'MEASURED_ADMISSION.json',dict(max_own_staging_seconds=setup,retained_original_full_work_seconds=work,margin=1.25,need_seconds=needed,cap_seconds=assignment['cap_seconds'],status='ADMIT'if needed<=assignment['cap_seconds']else'NO_FIT',timing_profiles_not_replayed=True))
 if needed>assignment['cap_seconds']:raise W.NoFit('original max staging plus1.25retained full production work exceeds new approved remaining cap')
 for reader,layer in [('oracle',44),('nla',42)]:
  clock.call(reader+'_setup',b.load_oracle if reader=='oracle'else b.load_nla);clock.call(reader+'_warmup_discarded',lambda reader=reader:b.native(reader,dummy,False));stage=out/reader;stage.mkdir()
  for k in range(0,len(items),32):
   units=items[k:k+32];h=acts[layer][k:k+32].copy();before=h.tobytes();got=clock.call(reader+'_native',lambda reader=reader,h=h:b.native(reader,h,False),real=True)
   require(h.tobytes()==before and len(got)==len(units)and all(len(x)==1 for x in got),'unaltered native grid')
   rows=[dict(id=x['id']+':'+reader+':0',unit_id=x['id'],feature=x['feature'],arm=x['arm'],reader=reader,repeat=0,**g[0])for x,g in zip(units,got)]
   write(stage/f'{k//32:06d}.json',rows)
  seal(stage,'STAGE_SEAL.json',experiment='E85',reader=reader,status='COMPLETE',n=400)

def main():
 p=argparse.ArgumentParser()
 for k in ['inputs','assets','assignment','out','releases','capture','cpu-release']:p.add_argument('--'+k,type=Path,required=True)
 for k in ['source-sha','input-sha','retained-source-sha']:p.add_argument('--'+k,required=True)
 p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 # The immutable original worker/contract/dependency source remains verified.
 plan,items,scores,downstream,limits,ass,end=W.preflight(a);require(plan['experiment']=='E85','E85 only')
 verify(Path(__file__).parent,'RETAINED_SOURCE_SEAL.json',a.retained_source_sha)
 units,acts=retained(items,a.capture,a.cpu_release);a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass)
 if a.dry_run:
  from test_worker import TinyRuntime
  b=TinyRuntime()
 else:
  from runtime import Runtime
  b=Runtime(a.assets);b.hardware_assignment=ass
 c=W.Clock(a.out,end,limits['seed_seconds_per_batch'],b)
 timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='COMPLETE'
 try:run(b,c,units,acts,a.out,ass)
 except W.NoFit as e:status='NO_FIT';write(a.out/'NO_FIT.json',dict(reason=str(e),no_scientific_stitching=True))
 except BaseException as e:write(a.out/'FAILURE.json',dict(error_type=type(e).__name__,reason=str(e)));raise
 finally:timer.cancel()
 outputs=sorted(p for reader in ['oracle','nla']for p in(a.out/reader).glob('[0-9]*.json'))
 first=min(outputs,key=lambda p:p.stat().st_mtime_ns)if outputs else None
 if status=='COMPLETE':require(len(outputs)==26 and sum(len(read(p))for p in outputs)==800,'full800 new native outputs')
 seal(a.out,'OUTPUT_SEAL.json',experiment='E85',status=status,synthetic=a.dry_run,retained_capture_sha256=CAPTURE,original_probe_sha256=PROBE,retained_source_sha256=a.retained_source_sha,first_output_evidence=None if first is None else dict(member=str(first.relative_to(a.out)),mtime_ns=first.stat().st_mtime_ns,sha256=sha(first)),original_cumulative_prior_seconds=ass['prior_seconds'],no_capture_or_probe_or_downstream_replay=True)
if __name__=='__main__':main()
