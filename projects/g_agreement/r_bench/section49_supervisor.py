"""Operational §49 supervisor. Stdlib-only; scientific registration stays frozen."""
from __future__ import annotations
import argparse, hashlib, json, os, signal, subprocess, sys, time
from pathlib import Path


def read(p): return json.loads(Path(p).read_text())
def save(p, v):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_suffix(p.suffix + '.tmp'); t.write_text(json.dumps(v, indent=2)+'\n'); t.replace(p)
def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''): h.update(b)
    return h.hexdigest()
def files(root): return sorted(p for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink())
def byte_sizes(roots):
    result = {}
    for root in roots:
        for p in files(root):
            try: result[str(p)] = p.stat().st_size
            except FileNotFoundError: pass
    return result

def kill_group(p):
    if p.poll() is not None: return
    os.killpg(p.pid, signal.SIGTERM)
    try: p.wait(timeout=5)
    except subprocess.TimeoutExpired: os.killpg(p.pid, signal.SIGKILL); p.wait()

def package(out):
    out = Path(out)
    excluded = {'manifest.json','mac_receipt.json','release.json','progress.txt'}
    m = {str(p.relative_to(out)):sha(p) for p in files(out) if p.name not in excluded and 'inputs' not in p.relative_to(out).parts}
    save(out/'manifest.json',m)
    return m

def receipt(local):
    local = Path(local); m = read(local/'manifest.json')
    for rel,h in m.items():
        p=(local/rel).resolve()
        if not p.is_relative_to(local.resolve()) or sha(p)!=h: raise ValueError('Pull hash mismatch '+rel)
    r={'manifest_sha256':sha(local/'manifest.json'),'files':m,'verified_at':time.time()}
    save(local/'mac_receipt.json',r); return r

def release(out):
    out=Path(out); r=read(out/'mac_receipt.json'); m=read(out/'manifest.json')
    if r['manifest_sha256']!=sha(out/'manifest.json') or r['files']!=m: raise ValueError('Receipt mismatch')
    for rel,h in m.items():
        if sha(out/rel)!=h: raise ValueError('Retained hash mismatch '+rel)
    save(out/'release.json',{'status':'VERIFIED_READY_TO_STOP','manifest_sha256':sha(out/'manifest.json'),'files':len(m)})

def supervise(cfg):
    root=Path(cfg['root']); out=root/'output'; ctl=root/'control'; out.mkdir(parents=True,exist_ok=True); ctl.mkdir(exist_ok=True)
    # Refuse any implicit resume / duplicate attempt.
    with (ctl/'supervisor.lock').open('x') as f: f.write(str(os.getpid()))
    (ctl/'supervisor.pid').write_text(str(os.getpid()))
    now=time.time(); deadline=cfg['deadline']; reserve=cfg['pull_reserve_s']
    if not cfg.get('test_mode'):
        native=dict(x.split('=',1) for x in Path('/proc/1/environ').read_text().split('\0') if '=' in x).get('RUNPOD_POD_ID')
        if native!=cfg['pod_id'] or cfg['gpu_count']!=1 or cfg.get('cap_seconds')!=9000 or deadline>cfg['created_epoch']+9000: raise ValueError('Native identity/budget mismatch')
        if not cfg['custody_acknowledged'] or not cfg['own_account_http200']: raise ValueError('Missing custody/account proof')
        if reserve<600 or cfg['stall_s']!=600: raise ValueError('Invalid production reserve/stall policy')
    env=os.environ.copy(); env.update(cfg.get('env',{})); env['RUNPOD_POD_ID']=cfg['pod_id']
    for key in ['HF_TOKEN','HUGGING_FACE_HUB_TOKEN']: env.pop(key,None)
    events=[]; error=None
    try:
        if now>=deadline-reserve: raise TimeoutError('No time before pull reserve')
        for step in cfg['steps']:
            name=step['name']; start=time.time(); before=byte_sizes(step.get('byte_roots',[])); last_growth=start
            save(ctl/'state.json',{'state':'RUNNING','stage':name,'time':start})
            with (out/(name+'.log')).open('w') as log:
                p=subprocess.Popen(step['argv'],cwd=cfg['cwd'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                save(ctl/'child.json',{'stage':name,'pid':p.pid,'started':start,'declared_byte_roots':step.get('byte_roots',[])})
                try:
                    while p.poll() is None:
                        t=time.time()
                        if t>=deadline-reserve: raise TimeoutError('Creation-based science cutoff')
                        if step.get('byte_roots'):
                            after=byte_sizes(step['byte_roots'])
                            growth=sum(max(0,n-before.get(k,0)) for k,n in after.items()); before=after
                            if growth:
                                last_growth=t
                                # Only actual downloaded/staged byte growth updates this watchdog signal.
                                with (ctl/'activity_bytes.txt').open('a') as f: f.write(f'{t} {name} {p.pid} +{growth}\n')
                            if t-last_growth>=cfg['stall_s']: raise TimeoutError('No download/staging byte growth for 600s: '+name)
                        time.sleep(cfg.get('poll_s',2))
                    if p.returncode: raise RuntimeError(f'{name} exit {p.returncode}')
                finally: kill_group(p)
            events.append({'stage':name,'exit':0,'seconds':time.time()-start})
    except Exception as exc: error=str(exc)
    # Logs closed before manifest; code, venv and model cache live outside output.
    save(out/'chain_result.json',{'status':'INCOMPLETE' if error else 'COMPLETE','error':error,'stages':events,'finished_at':time.time()})
    for name in ['child.json','activity_bytes.txt','launcher.log']:
        if (ctl/name).exists(): (out/name).write_bytes((ctl/name).read_bytes())
    package(out)
    save(ctl/'state.json',{'state':'AWAITING_PULL','science_status':'INCOMPLETE' if error else 'COMPLETE','time':time.time()})
    try:
        while not (out/'mac_receipt.json').exists():
            if time.time()>=deadline-(.1 if cfg.get('test_mode') else 60): raise TimeoutError('Final pull receipt deadline')
            time.sleep(cfg.get('poll_s',2))
        release(out)
        save(ctl/'state.json',{'state':'VERIFIED_READY_TO_STOP','science_status':'INCOMPLETE' if error else 'COMPLETE','time':time.time()})
        return 1 if error else 0
    except Exception as exc:
        save(ctl/'state.json',{'state':'PULL_FAILED','error':str(exc),'time':time.time()}); return 2


def main():
    p=argparse.ArgumentParser(); p.add_argument('config'); a=p.parse_args(); sys.exit(supervise(read(a.config)))
if __name__=='__main__': main()
