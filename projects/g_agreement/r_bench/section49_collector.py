"""Mac-owned automatic log pulls, final receipt and exact-ID stop. No key on pod."""
from __future__ import annotations
import argparse, json, os, shlex, shutil, subprocess, time
from pathlib import Path
from projects.g_agreement.r_bench.section49_supervisor import read,save,receipt,sha

class Transport:
    def __init__(self,c): self.c=c; self.local=Path(c['local']); self.local.mkdir(parents=True,exist_ok=True)
    def ssh(self,cmd):
        return subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-p',str(self.c['port']),'-i',self.c['key'],self.c['host'],cmd],check=True,capture_output=True,text=True,timeout=min(60,max(1,self.c['deadline']-time.time())))
    def state(self):
        if self.c.get('local_transport'): return read(Path(self.c['root'])/'control/state.json')
        return json.loads(self.ssh('cat '+shlex.quote(self.c['root']+'/control/state.json')).stdout)
    def pull(self,final=False):
        dest=self.local/('final' if final else 'logs'); dest.mkdir(exist_ok=True)
        if self.c.get('local_transport'):
            src=Path(self.c['root'])/'output'
            for p in src.rglob('*'):
                if p.is_file() and (final or p.suffix in ('.log','.json','.txt')):
                    q=dest/p.relative_to(src); q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,q)
        else:
            ssh=shlex.join(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-p',str(self.c['port']),'-i',self.c['key']])
            args=['rsync','-az','--timeout=45','-e',ssh]
            if not final: args+=['--include=*/','--include=*.log','--include=*.json','--include=*.txt','--exclude=*']
            args += [self.c['host']+':'+self.c['root']+'/output/',str(dest)+'/']
            subprocess.run(args,check=True,timeout=min(480,max(1,self.c['deadline']-time.time()-30)))
        if not final:
            control=self.local/'control'; control.mkdir(exist_ok=True)
            if self.c.get('local_transport'):
                for p in (Path(self.c['root'])/'control').glob('*'):
                    if p.is_file(): shutil.copy2(p,control/p.name)
            else:
                subprocess.run(['rsync','-az','--timeout=45','-e',ssh,self.c['host']+':'+self.c['root']+'/control/',str(control)+'/'],check=True,timeout=60)
        return dest
    def send_receipt(self,p):
        if self.c.get('local_transport'):
            tmp=Path(self.c['root'])/'output/mac_receipt.json.tmp'; shutil.copy2(p,tmp);tmp.replace(tmp.with_suffix(''))
        else:
            subprocess.run(['scp','-o','BatchMode=yes','-o','ConnectTimeout=10','-P',str(self.c['port']),'-i',self.c['key'],str(p),self.c['host']+':'+self.c['root']+'/output/mac_receipt.json.tmp'],check=True,timeout=30)
            self.ssh('mv '+shlex.quote(self.c['root']+'/output/mac_receipt.json.tmp')+' '+shlex.quote(self.c['root']+'/output/mac_receipt.json'))
    def stop(self):
        if self.c.get('local_transport'): save(self.local/'stop.json',{'pod':self.c['pod_id'],'status':'EXITED','simulated':True}); return
        # Account credential stays in the existing Mac API helper.
        pod=self.c['pod_id']; api=self.c['api']
        def call(q): return json.loads(subprocess.run(['bash',api,q],capture_output=True,text=True,check=True,timeout=30).stdout)
        prior=call('query { pod(input:{podId:"'+pod+'"}) { id desiredStatus } }')['data']['pod']
        if prior['id']!=pod: raise ValueError('Wrong own-account pod')
        call('mutation { podStop(input:{podId:"'+pod+'"}) { id desiredStatus } }')
        for _ in range(12):
            check=call('query { pod(input:{podId:"'+pod+'"}) { id desiredStatus } }')['data']['pod']
            if check['id']==pod and check['desiredStatus']=='EXITED':
                save(self.local/'stop.json',{'pod':pod,'status':'EXITED','confirmed_at':time.time()}); return
            time.sleep(5)
        raise RuntimeError('Stop not independently confirmed')

def collect(c):
    t=Transport(c); last=0.; sent=False; snapshots=0
    with (t.local/'collector.lock').open('x') as f: f.write(str(os.getpid()))
    while time.time()<c['deadline']:
        try:
            state=t.state()
            if time.time()-last>=c.get('log_interval_s',600):
                t.pull(); last=time.time(); snapshots+=1
                save(t.local/'log_pull_receipt.json',{'time':last,'snapshots':snapshots})
            if state['state']=='AWAITING_PULL' and not sent:
                local=t.pull(final=True); receipt(local); t.send_receipt(local/'mac_receipt.json'); sent=True
            if state['state']=='VERIFIED_READY_TO_STOP':
                local=t.pull(final=True); receipt(local)
                release=read(local/'release.json')
                if release['status']!='VERIFIED_READY_TO_STOP' or release['manifest_sha256']!=sha(local/'manifest.json'): raise ValueError('Bad remote release')
                t.stop(); return 0
            if state['state']=='PULL_FAILED': raise RuntimeError('Remote final pull failed')
        except (OSError,ValueError,subprocess.SubprocessError,RuntimeError,KeyError) as exc:
            save(t.local/'collector_error.json',{'time':time.time(),'error':str(exc)})
        time.sleep(c.get('poll_s',5))
    save(t.local/'collector_failure.json',{'status':'INCOMPLETE_PULL_DEADLINE','time':time.time()}); return 2

def main():
    import sys
    p=argparse.ArgumentParser();p.add_argument('config');a=p.parse_args();sys.exit(collect(read(a.config)))
if __name__=='__main__':main()
