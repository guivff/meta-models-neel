"""Operational pause after the original first retained E98 native sample; no model or sampling changes."""
from pathlib import Path
import importlib.util,json,time,sys,os,signal,threading

def validate_admission(a,assignment,now):
    import math
    if (a['experiment']!='E98'or a['pod_id']!=assignment['pod_id']or a['admitted_epoch']>assignment['timing_deadline_epoch']
        or a['deadline_epoch']>assignment['deadline_epoch']or a['deadline_epoch']<=now
        or a['deadline_epoch']!=assignment['custody_start_epoch']+a['cap_seconds']
        or a['cap_seconds']!=math.ceil(a['max_measured_setup_seconds']+1.25*a['measured_work_seconds'])):raise ValueError('Nonrenewable measured admission')

def install(worker,assignment,timer):
    original=worker.Clock.fits
    def fits(self,remaining):
        admitted=original(self,remaining)
        if len(self.samples)==1:
            ready=dict(ready_epoch=time.time(),sample_seconds=self.samples[0],retained_samples=1,records=len(list((self.out/'records').glob('*.json'))),initial_fit=admitted)
            worker.write(self.out/'MEASURED_TIMING_READY.json',ready)
            if not admitted:return False
            p=self.out.parent/'MEASURED_PRODUCTION.json'
            while not p.exists():
                if time.time()>=assignment['timing_deadline_epoch']-30:raise TimeoutError('Fixed timing gate before sample2')
                time.sleep(.2)
            a=json.loads(p.read_text());validate_admission(a,assignment,time.time());self.deadline=min(self.deadline,a['deadline_epoch']);timer.cancel()
            revised=dict(assignment,cap_seconds=a['cap_seconds'],deadline_epoch=self.deadline)
            worker.write(self.out/'MEASURED_PRODUCTION.json',a);worker.write(self.out/'ASSIGNMENT.json',revised);worker.write(self.out.parent/'assignment.json',revised)
            return original(self,remaining)
        return admitted
    worker.Clock.fits=fits

def main():
    path=Path(sys.argv[1]);sys.argv=[str(path),*sys.argv[2:]]
    assignment=json.loads(Path(sys.argv[sys.argv.index('--assignment')+1]).read_text())
    spec=importlib.util.spec_from_file_location('frozen_e98_worker',path);worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    timer=threading.Timer(max(0,assignment['timing_deadline_epoch']-time.time()-30),lambda:os.kill(os.getpid(),signal.SIGINT));timer.daemon=True;timer.start();install(worker,assignment,timer)
    try:worker.main()
    finally:timer.cancel()
if __name__=='__main__':main()
