"""Detached §79 process deadline; Mac guards independently own pod custody."""
import argparse,json,os,signal,subprocess,time
from pathlib import Path
from . import protocol as P,corpus as C

def output_paths(out,workspace='/workspace/s79'):return {'status':Path(out)/'status.s79.json','pid':Path(workspace)/'job.pid','log':Path(workspace)/'job.s79.log'}

def child_deadline(a,out,native):
 stage=Path(out)/'native/stage_complete.s79.json'
 if not native or not stage.exists():return a['setup_deadline_epoch']
 try:first=float(json.loads(stage.read_text())['at'])
 except (json.JSONDecodeError,KeyError):return a['setup_deadline_epoch'] # Writer may be between open and flush; retain stricter clock.
 return P.science_deadline(a,first)

def run(assignment,bank,out):
 os.environ.update(HF_HOME='/workspace/s79/hf',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1')
 P.verify_freeze();a=P.admit(assignment);base=Path(out);base.mkdir(parents=True,exist_ok=False);output_paths(base)['pid'].write_text(str(os.getpid()))
 commands=[['bash','projects/g_agreement/blindspot/screens/bootstrap.sh'],['/workspace/s79-venv/bin/python','-B','-m','projects.g_agreement.blindspot.screens.stage','--assignment',str(assignment),'--out',str(base/'stage')],['/workspace/s79-venv/bin/python','-B','-m','projects.g_agreement.blindspot.screens.run','--assignment',str(assignment),'--bank',str(bank),'--out',str(base/'native'),'--assets',str(base/'stage/assets.s79.json')]]
 for command in commands:
  child=subprocess.Popen(command,start_new_session=True)
  while child.poll() is None:
   if time.time()>=child_deadline(a,base,command is commands[-1]):
    os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    C.save(output_paths(base)['status'],{'status':'INCOMPLETE','reason':'science cutoff reserves verified retrieval'});return 2
   time.sleep(1)
  if child.returncode:C.save(output_paths(base)['status'],{'status':'INCOMPLETE','reason':'child failed','exit':child.returncode,'command':command});return child.returncode
 C.save(output_paths(base)['status'],{'status':'NATIVE_SCORES_SEALED_PULL_AND_WARM_RELEASE','at':time.time()});return 0

def main():
 p=argparse.ArgumentParser()
 for k in ['assignment','bank','out']:p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args();raise SystemExit(run(a.assignment,a.bank,a.out))
if __name__=='__main__':main()
