"""E140 operator transport and original creation-clock accounting; owner science unchanged."""
import argparse,hashlib,json,os,signal,threading,time,math
from pathlib import Path
from e140_dev3_clock254 import SEEDS,forecast,retain,screen_remaining,main_remaining
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.new');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def verify(root,name,digest):
 p=Path(root)/name;assert sha(p)==digest,'seal pin'
 s=read(p)
 for n,h in s['files'].items():assert sha(Path(root)/n)==h,'member pin '+n
 return s
class Clock:
 def __init__(self,ass,out):self.ass=ass;self.out=out;self.maxima=SEEDS.copy();self.events=[]
 def fit(self,remaining):
  f=forecast(time.time()-self.ass['pod_created_epoch'],remaining,self.maxima,min(self.ass['cap_seconds'],self.ass['absolute_deadline_epoch']-self.ass['pod_created_epoch']));write(self.out/'FORECAST.json',f);return f['status']=='ADMIT'
 def call(self,phase,fn):
  assert time.time()<self.ass['absolute_deadline_epoch']-60,'original absolute reserve'
  t=time.monotonic();v=fn()
  import torch
  torch.cuda.synchronize();dt=time.monotonic()-t;retain(self.maxima,phase,dt);self.events.append(dict(phase=phase,seconds=dt));write(self.out/'TIMINGS.json',self.events);return v

def run(xs,a,out,c):
 from projects.g_agreement.e101.runner import dependencies
 from projects.g_agreement.e140 import runner
 rt=dependencies()[1](a.assets)
 pending=screen_remaining(85,0,36);pending['base']=1
 if not c.fit(pending):return 'NO_FIT'
 c.call('base',rt.load_base)
 model,tok,cm=rt.subject()
 original=runner.generation_batch;generation_count=[0]
 def generation(*args,**kw):
  phase='generation_cold'if generation_count[0]==0 else'generation_post';v=c.call(phase,lambda:original(*args,**kw));generation_count[0]+=1;return v
 runner.generation_batch=generation
 def check_screen(n,elapsed,maximum):return c.fit(screen_remaining(85,85-n,36))
 with cm:status=runner.screen(model,tok,xs,out/'screen',check_screen,gpu_type='H200')
 # Release ALL local subject references before main_job manages original model lifecycle.
 del model,tok,cm
 if status!='COMPLETE':return status
 screen_sha=sha(out/'screen/OUTPUT_SEAL.json');write(out/'SCREEN_READY.json',dict(screen_sha256=screen_sha,screen_candidates=300,screen_prompts=600,original_deadline=c.ass['absolute_deadline_epoch']))
 wait=time.monotonic()
 while not Path('CPU_DISPOSITION.json').exists():
  if time.monotonic()-wait>180 or time.time()>=c.ass['absolute_deadline_epoch']-60:return 'NO_FIT'
  time.sleep(1)
 disposition=read('CPU_DISPOSITION.json');assert disposition['screen_output_sha256']==screen_sha
 assert disposition['action']in('MAIN','SCREEN_RESULTS_ONLY')
 retain(c.maxima,'mac_roundtrip',max(.001,time.monotonic()-wait))
 if disposition['action']=='SCREEN_RESULTS_ONLY':return 'SCREEN_RESULTS_ONLY'
 mainsha=disposition['input_sha256'];items=runner.load(Path('main_inputs'),mainsha,'main');N=len(list(runner.batches(items,8)))
 write(out/'CPU_DISPOSITION.json',disposition);write(out/'MAIN_INPUT_SEAL.json',read('main_inputs/INPUT_SEAL.json'))
 originalcap=runner.capture_batch;originalnative=runner.oracle_batch;originalsetup=rt.load_oracle
 runner.capture_batch=lambda *args,**kw:c.call('capture',lambda:originalcap(*args,**kw))
 runner.oracle_batch=lambda *args,**kw:c.call('native',lambda:originalnative(*args,**kw))
 rt.load_oracle=lambda:c.call('oracle_setup',originalsetup)
 calls=[0]
 def check_main(n,elapsed,maximum):
  remaining=main_remaining(N,calls[0]);calls[0]+=1;return c.fit(remaining)
 return runner.main_job(rt,items,out/'main',check_main,gpu_type='H200')

def main():
 p=argparse.ArgumentParser()
 for n in('inputs','assets','assignment','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
 for n in('source-sha','input-sha'):p.add_argument('--'+n,required=True)
 p.add_argument('--validate-only',action='store_true');a=p.parse_args();verify(Path.cwd(),str(a.source_seal),a.source_sha)
 from projects.g_agreement.e140 import runner
 from projects.g_agreement.e101.runner import dependencies
 xs=runner.load(a.inputs,a.input_sha,'screen');assert len(xs)==600 and runner.screen_scope(a.inputs,a.input_sha,xs)['screen_candidates']==300
 if a.validate_only:print('VALIDATE_OK E140 300pairs600prompts original source imports; no weights');return
 ass=read(a.assignment);assert ass['experiment']=='E140'and ass['pod_id']==os.environ.get('RUNPOD_POD_ID')and ass['gpu_type']=='H200'and ass['allocation_verified']and ass['daily_budget_verified']
 assert ass['source_sha256']==a.source_sha and ass['input_sha256']==a.input_sha and ass['assets_sha256']==sha(a.assets)
 assert ass['cap_seconds']==9300 and ass['absolute_deadline_epoch']==min(ass['pod_created_epoch']+ass['cap_seconds'],1793364600) and ass['pod_created_epoch']<1793354400
 import torch
 assert torch.cuda.is_available()and torch.cuda.device_count()==1 and'H200'in torch.cuda.get_device_name(0)
 a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);write(a.out/'INVENTORY.json',dict(ids=[x['id']for x in xs],source_sha256=a.source_sha,input_sha256=a.input_sha,screen_candidates=300))
 c=Clock(ass,a.out);status='FAILED';timer=threading.Timer(max(0,ass['absolute_deadline_epoch']-time.time()-30),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
 try:status=run(xs,a,a.out,c)
 except BaseException as e:write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:500]));raise
 finally:
  timer.cancel();files=[q for q in a.out.rglob('*')if q.is_file()and q!=a.out/'OUTPUT_SEAL.json'];write(a.out/'OUTPUT_SEAL.json',dict(experiment='E140',status=status,source_sha256=a.source_sha,input_sha256=a.input_sha,labels_cpu_only=True,judging=False,outputs_unopened=True,files={str(q.relative_to(a.out)):sha(q)for q in files}))
if __name__=='__main__':main()
