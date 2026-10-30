"""E62 existing-pod stage: parity, sealed all-position capture, forecast go-signal, readers."""
import argparse,time,threading,os,signal,math
from pathlib import Path
from runtime62 import *
import parity_gate

class Budget:
 def __init__(self,end):self.end=end;self.observed={}
 def call(self,phase,fn,remaining_units=0):
  require(time.time()<self.end-60,'E62 custody reserve');t=time.monotonic();v=fn();self.observed[phase]=max(self.observed.get(phase,0),time.monotonic()-t)
  require(time.time()+1.5*self.observed[phase]*remaining_units<self.end-60,'E62 NO_FIT '+phase);return v

def main():
 p=argparse.ArgumentParser()
 for key in ('inputs','assets','assignment','out','go'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();ass=read(a.assignment)
 require(ass['existing_pod'] is True and ass['gpu_count']==1 and 0<ass['cap_seconds']<=14400,'E62 existing pod within twice registered7200s total')
 require(ass['total_E62_custody_seconds']<=14400 and ass['cap_seconds']<=ass['total_E62_custody_seconds'],'integrator cumulative E62 custody certification')
 end=min(ass['stage_started_epoch']+ass['cap_seconds'],ass['absolute_deadline_epoch']);require(math.isfinite(end),'finite deadline');budget=Budget(end)
 verify(HERE,'SOURCE_SEAL.json',ass['source_seal_sha256']);verify(a.inputs,'INPUT_SEAL.json',ass['input_seal_sha256'])
 for path,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/path)==digest,'dependency identity')
 items=read(a.inputs/'items.json');validate_items(items);a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'ASSIGNMENT.json',ass)
 timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:
  backend=Backend(ROOT,a.assets,{'gpu_type':'H200'});budget.call('oracle_setup',backend.load_oracle)
  parity=a.out/'parity';parity.mkdir();parity_gate.run_gate(backend,budget,parity,parity_gate.load_inputs({'path':str(a.inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256}))
  cap=acquire_capture(items,backend,budget,a.out,{'source_seal_sha256':ass['source_seal_sha256'],'input_seal_sha256':ass['input_seal_sha256'],'pod_id':ass['pod_id']})
  dump(a.out/'CAPTURE_READY.json',{'capture_seal_sha256':sha(cap/'CAPTURE_SEAL.json'),'reader_outputs':0})
  while not a.go.exists():
   require(time.time()<end-60,'forecast wait exceeds custody');time.sleep(1)
  go=read(a.go);require(go['reader_launch_authorized'] is True and go['capture_seal_sha256']==sha(cap/'CAPTURE_SEAL.json') and go['input_seal_sha256']==ass['input_seal_sha256'] and len(go['E62_JFORECAST_sha256'])==64,'integrator forecast-bound go signal')
  dump(a.out/'GO_RECEIPT.json',go);acquire_readers(items,backend,budget,a.out,cap)
  dump(a.out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':end,'phase_max_seconds':budget.observed})
  seal(a.out,'OUTPUT_SEAL.json',dict(ass,experiment='E62',status='COMPLETE'))
 except BaseException as e:dump(a.out/'FAILURE.json',{'error':str(e)});raise
 finally:timer.cancel()
if __name__=='__main__':main()
