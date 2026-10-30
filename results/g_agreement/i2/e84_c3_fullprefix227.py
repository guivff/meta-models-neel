"""Frozen E84 full-prefix acquisition; no truth/labels/joins enter GPU runtime.
One creation clock, dev captures only, CPU gate before test-only reader/baseline.
"""
import argparse,json,time,os,signal,threading,hashlib,math
from pathlib import Path
import numpy as np
from runtime import Runtime
from contract import read,write,sha,require

def validate(items,baseline):
 require(len(items)==300 and len({x['id']for x in items})==300,'full frozen300')
 require(sum(x['split']=='dev'for x in items)==100 and sum(x['split']=='test'for x in items)==200,'original disjoint splits')
 require(len(baseline)==200 and {x['id']for x in baseline}=={x['id']for x in items if x['split']=='test'},'exact200test baseline')
 for x in items:
  require(set(x)=={'id','input_ids','prompt','read_position','reader_allowed','split'},'public allowlist')
  require(x['reader_allowed']==(x['split']=='test')and x['read_position']==len(x['input_ids'])-1,'final original read token')
 require(max(len(x['input_ids'])for x in items)==71574,'frozen full longest prefix')
 return sorted(items,key=lambda x:(-len(x['input_ids']),x['id']))

def measured_fit(elapsed,capture_seconds,captures_remaining,text_upper,native_upper,cap=24469):
 require(capture_seconds and all(x>0 for x in capture_seconds),'actual timings')
 need=elapsed+1.25*(max(capture_seconds)*captures_remaining+text_upper+native_upper)+60
 return dict(status='PASS'if need<=cap else'NO_FIT',elapsed_setup_and_profile_seconds=elapsed,max_capture_seconds=max(capture_seconds),captures_remaining=captures_remaining,text_upper_seconds=text_upper,native_upper_seconds=native_upper,margin=1.25,need_seconds=need,cap_seconds=cap)

def run(a,b):
 ass=read(a.assignment);created=ass['pod_created_epoch'];end=ass['absolute_deadline_epoch'];require(ass['experiment']=='E84'and ass['cap_seconds']==24469 and end==created+24469,'explicit measured custody cap')
 require(time.time()<created+900 and sha(a.inputs)==a.inputs_sha256 and sha(a.baseline)==a.baseline_sha256,'frozen public input binding/setup900')
 items=read(a.inputs);base=read(a.baseline);ordered=validate(items,base);a.out.mkdir(exist_ok=False)
 events=[]
 def timed(name,fn):
  require(time.time()<end-60,'original deadline');t=time.monotonic();value=fn();b.sync();events.append(dict(phase=name,seconds=time.monotonic()-t));write(a.out/'TIMINGS.json',events,replace=True);return value
 timed('load_base',b.load_base);b.seed(20261029);require(time.time()<created+900,'setup900')
 # Longest-context synthetic text warmup is discarded, never scored/selected.
 model,tok,cm=b.subject();token=tok.encode(' the',add_special_tokens=False)[0];longest=max(len(x['input_ids'])for x in base)
 timed('synthetic_longest_text_discarded',lambda:b.text([[token]*longest],max_new_tokens=128));text_upper=events[-1]['seconds']*200
 # Exact reader forecast comes from immutable original retained-source timing.
 timing=read(Path(__file__).with_name('E84_READER_TIMING.json'));require(sha(Path(__file__).with_name('E84_READER_TIMING.json'))==a.timing_sha256,'timing source pinned')
 native_upper=timing['full_native_work_seconds_upper']
 acts={42:{},44:{}};durations=[];status='COMPLETE';capture_complete=False;readers_complete=False
 for i,x in enumerate(ordered):
  if i>=3:
   fit=measured_fit(time.time()-created,durations,len(ordered)-i,text_upper,native_upper);write(a.out/'MEASURED_ADMISSION.json',fit,replace=True)
   if fit['status']=='NO_FIT':status='NO_FIT';break
  value=timed('capture:'+x['id'],lambda x=x:b.capture([dict(id=x['id'],text=x['prompt'],ids=x['input_ids'],read_index=x['read_position'])]));durations.append(events[-1]['seconds'])
  for layer in (42,44):
   v=value[layer];require(v.shape==(1,5120)and np.isfinite(v).all(),'finite full readpoint vectors');acts[layer][x['id']]=v[0]
  target=a.out/'capture'/ (x['id']+'.npz');target.parent.mkdir(exist_ok=True);np.savez(target,**{str(k):value[k]for k in (42,44)})
 if len(acts[42])==300:
  capture_complete=True;capdir=a.out/'capture';write(capdir/'ORDER.json',[x['id']for x in items]);write(capdir/'CAPTURE_SEAL.json',dict(experiment='E84',status='COMPLETE',items=300,blocks=[44,42],complete_prefix=True,cropped=False,files={p.name:sha(p)for p in capdir.iterdir()if p.is_file()}));write(a.out/'WAITING_CPU_GATE.json',dict(capture_seal_sha256=sha(capdir/'CAPTURE_SEAL.json'),deadline=end))
  while not a.release.exists():
   require(time.time()<end-60,'CPU gate wait within original deadline');time.sleep(1)
  gate=read(a.release);require(gate['capture_seal_sha256']==sha(capdir/'CAPTURE_SEAL.json')and gate['test_AUROC_sites']==[44,42]and gate['labels_cpu_only'] is True,'original CPU gate binding')
  if True:  # Generic baseline is retained even when both native probes fail.
   require(set(gate['released_ids'])=={x['id']for x in base},'all200 test only; no selection')
   (a.out/'text_generic').mkdir()
   for x in sorted(base,key=lambda x:(-len(x['input_ids']),x['id'])):
    v=timed('text_generic:'+x['id'],lambda x=x:b.text([x['input_ids']],max_new_tokens=128));write(a.out/'text_generic'/(x['id']+'.json'),dict(id=x['id'],output=v[0]))
   # Batch32 native source was pre-output tested; no capture/profile replay.
   b.native_batch_size=32;test=[x for x in items if x['split']=='test']
   require(set(gate['probe_pass_by_reader'])=={'oracle','nla'},'independent reader gates')
   oracle_loaded=False
   for reader,layer,load in [('oracle',44,b.load_oracle),('nla',42,b.load_nla)]:
    if not gate['probe_pass_by_reader'][reader]:continue
    if reader=='nla' and not oracle_loaded:timed('oracle_backend_setup_for_nla',b.load_oracle)
    timed(reader+'_setup',load);(a.out/reader).mkdir()
    if reader=='oracle':oracle_loaded=True
    for start in range(0,200,32):
     xs=test[start:start+32];v=timed(reader+'_native',lambda xs=xs,reader=reader,layer=layer:b.native(reader,np.array([acts[layer][x['id']]for x in xs]),False));require(len(v)==len(xs)and all(len(g)==1 for g in v),'one greedy native each')
     write(a.out/reader/f'{start:04d}.json',[dict(id=x['id'],output=g[0])for x,g in zip(xs,v)])
   readers_complete=True
 files=[p for p in a.out.rglob('*')if p.is_file()];scientific=[p for p in files if p.suffix in ('.npz','.json')and p.name not in ('TIMINGS.json','MEASURED_ADMISSION.json')];first=min(scientific,key=lambda p:p.stat().st_mtime_ns)if scientific else None
 write(a.out/'OUTPUT_SEAL.json',dict(experiment='E84',status=status,source_sha256=a.source_sha256,input_sha256=a.inputs_sha256,baseline_sha256=a.baseline_sha256,capture_complete=capture_complete,capture_items=len(acts[42]),readers_complete=readers_complete,independent_native_probe_gates=True,generic_baseline_retained=True,full_prefix_no_truncation=True,old_outputs_reused=False,first_output_evidence=None if first is None else dict(member=str(first.relative_to(a.out)),sha256=sha(first),mtime_ns=first.stat().st_mtime_ns),files={str(p.relative_to(a.out)):sha(p)for p in files}))

def main():
 p=argparse.ArgumentParser()
 for k in ['inputs','baseline','assets','assignment','out','release']:p.add_argument('--'+k,type=Path,required=True)
 for k in ['inputs-sha256','baseline-sha256','timing-sha256','source-sha256']:p.add_argument('--'+k,required=True)
 a=p.parse_args();end=read(a.assignment)['absolute_deadline_epoch'];timer=threading.Timer(max(0,end-time.time()-10),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:run(a,Runtime(a.assets))
 finally:timer.cancel()
if __name__=='__main__':main()
