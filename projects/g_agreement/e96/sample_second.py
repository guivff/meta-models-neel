"""Second attempt, §204 deviation3: original science with audited timing-only adaptation."""
import argparse,inspect,json
from pathlib import Path
from . import sample as original
from .timing3899 import digest,remaining
BaseClock=original.Clock
OriginalExecute=original.execute
ANCHOR="forecast=1.5*(sum(observed)/len(observed))*(len(own)-n-1) if observed else 0"
REPLACEMENT="forecast=clock.remaining_forecast(phase+'_'+reader,len(own)-n-1,observed)"

def runtime():
 source=inspect.getsource(OriginalExecute)
 if source.count(ANCHOR)!=1:raise ValueError('original timing guard anchor changed')
 patched=source.replace(ANCHOR,REPLACEMENT,1);ns=dict(original.__dict__);exec(compile(patched,original.__file__+'[deviation3 timing-only]','exec'),ns)
 return ns['execute'],source,patched

class Clock(BaseClock):
 def __init__(self,out,end,profile):
  super().__init__(out,end);self.profile=profile;self.setup_spent=0
  original.write(out/'TIMING_ADMISSION.json',profile)
  original.write(out/'EXECUTED_TIMING_RUNTIME.json',{'original_execute_sha256':__import__('hashlib').sha256(runtime()[1].encode()).hexdigest(),'executed_execute_sha256':__import__('hashlib').sha256(runtime()[2].encode()).hexdigest(),'patch':'only forecast expression replaced; all first batches/rows/seeds/decoding retained'})
 def call(self,phase,fn):
  value=super().call(phase,fn)
  if phase.endswith('_setup'):
   self.setup_spent+=self.events[-1]['seconds']
   if self.setup_spent>self.profile['setup_cap_seconds']:raise TimeoutError('maximum-measured setup cap exceeded')
  return value
 def remaining_forecast(self,phase,left,observed):return remaining(self.profile,phase,left,observed,self.setup_spent)

def main():
 parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--assignment',type=Path,required=True);args,_=parser.parse_known_args();ass=json.loads(args.assignment.read_text());path=Path(ass['timing_admission_path']);profile=json.loads(path.read_text())
 if digest(path)!=ass['timing_admission_sha256'] or digest(original.__file__)!=profile['original_sample_sha256'] or profile['authority']!='3899e1ea073f8609f33fb35b5ce1863c6223961f':raise ValueError('committed operational profile/source binding')
 execute,source,patched=runtime();original.execute=execute;original.Clock=lambda out,end:Clock(out,end,profile);original.main()
if __name__=='__main__':main()
