"""§172 clarification3: append NLA native only; never repeat capture, Oracle or probes."""
import argparse,json,time,threading,os,signal
from pathlib import Path
import numpy as np
from contract56 import *
from worker56 import Backend,readout_records
from native_nla512 import native_nla,truncation_summary

def main():
 raise RuntimeError('SUPERSEDED by 8c66b004; no slot1 Oracle output exists')
 p=argparse.ArgumentParser()
 for key in ('inputs','original','receipt','assets','assignment','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();ass=read(a.assignment);plan=read(HERE/'NLA_RERUN_BINDING.json');exp=ass['experiment'];require(exp in ('E56','E57') and ass['slot']==1,'slot1native rerun only')
 binding=plan[exp];receipt=read(a.receipt);require(receipt['verified'] is True and receipt['pod_id']=='4tp5igfxd3kv6t','verified original slot1')
 original=verify(a.original,'OUTPUT_SEAL.json',receipt['output_seal_sha256']);require(original['source_seal_sha256']==binding['original_source_seal_sha256'] and original['input_seal_sha256']==binding['input_seal_sha256'] and original['slot']==1,'original source/input identity')
 cap=a.original/'capture';verify(cap,'CAPTURE_SEAL.json');verify(a.inputs,'INPUT_SEAL.json',binding['input_seal_sha256']);verify(HERE,'SOURCE_SEAL.json',ass['source_seal_sha256'])
 for path,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/path)==digest,'dependency pin')
 require(ass['existing_pod'] is True and ass['gpu_count']==1 and 60<ass['cap_seconds']<=min(1800,ass['remaining_registered_GPU_seconds']),'retry within remaining registered custody')
 start=time.time();end=min(start+ass['cap_seconds'],ass['absolute_deadline_epoch']);require(start<end-60,'custody reserve')
 require(not a.out.resolve().is_relative_to(a.original.resolve()),'do not write original artifacts');a.out.mkdir(parents=True,exist_ok=False)
 dump(a.out/'ASSIGNMENT.json',dict(ass,stage_started_epoch=start));timer=threading.Timer(end-start,lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  backend=Backend(ROOT,a.assets,{'gpu_type':'H200'});backend.load_nla();h=np.load(cap/'acts42.npy',mmap_mode='r');order=read(cap/'items.order.json');ix={k:i for i,k in enumerate(order)};items={x['id']:x for x in read(a.inputs/'items.json')}
  if exp=='E56':
   rows=read(a.inputs/'SHARDS.json')['rows']['1'];samples=read(a.inputs/'SAMPLING.json')['native_ids']
  else:
   rp=read(a.inputs/'RUN_PLAN.json');rows=rp['shards']['1'];samples=rp['native_ids']
  jobs=[]
  for row in rows:
   for i in range(0,40,8):
    ids=samples[row][i:i+8];jobs.append(('text',[items[k] for k in ids],np.array(h[[ix[k] for k in ids]],dtype=np.float32)))
  if exp=='E56':
   selected=read(a.inputs/'SHARDS.json')['injection_rows']['1'];inj=[x for x in read(a.inputs/'injection/ITEMS.json')['items'] if x['row'] in selected];v=np.load(a.inputs/'injection/INPUT_VECTORS.npz')['activations']
   for i in range(0,len(inj),8):
    units=inj[i:i+8];jobs.append(('injection',units,v[[x['index'] for x in units]].copy()))
  records=[];worst=0
  for n,(kind,units,values) in enumerate(jobs):
   require(time.time()<end-60,'retry reserve');t=time.monotonic();outputs=native_nla(backend.nla,values,k=8);worst=max(worst,time.monotonic()-t);records+=readout_records('nla',units,outputs,kind)
   require(time.time()+1.5*worst*(len(jobs)-n-1)<end-60,'NO_FIT')
  with (a.out/'nla_native.jsonl').open('x') as f:
   for x in records:f.write(json.dumps(x,allow_nan=False)+'\n')
  if exp=='E57':
   import sys
   sys.path.insert(0,str(HERE.parents[1]/'e57/job'))
   from counts57 import count_item
   counted=[]
   for unit_id in sorted({r['unit_id'] for r in records if r['feature'] in ('category_switch','capacity_list')}):
    counted.append(count_item([r for r in records if r['unit_id']==unit_id],rp['count_metadata'][unit_id]))
   dump(a.out/'COUNTS.json',counted)
  dump(a.out/'NLA_TRUNCATION.json',truncation_summary(records));dump(a.out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':end})
  seal(a.out,'OUTPUT_SEAL.json',{'experiment':exp+'_NLA_NATIVE_RERUN','slot':1,'pod_id':ass['pod_id'],'source_seal_sha256':ass['source_seal_sha256'],'input_seal_sha256':binding['input_seal_sha256'],'original_output_seal_sha256':sha(a.original/'OUTPUT_SEAL.json'),'original_capture_seal_sha256':sha(cap/'CAPTURE_SEAL.json'),'status':'COMPLETE','oracle_repeated':False,'capture_repeated':False})
 except BaseException as error:dump(a.out/'FAILURE.json',{'error':str(error)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
