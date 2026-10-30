"""E97 v2 capture only. No production reader entry point or GO handling."""
from pathlib import Path
import argparse, hashlib, json, os, signal, sys, threading, time
from datetime import datetime, timezone
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
PUBLIC_SHA='22a5870f5ab41e520787b88c79dab3af463bfb36461edeea518bc2501488a6ef'
BANK_SHA='2afa89f0e551274b82368075338f7b117dcbbe97b403bf4a29d0a6b442ea4f08'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    p=Path(p);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n');os.replace(t,p)
def validate(items):
    if len(items)!=6720 or len({x['item_id'] for x in items})!=6720:raise ValueError('Exact v2 inventory required')
    if sum(x['split']=='test' for x in items)!=3360 or sum(x['split']=='dev' for x in items)!=3360:raise ValueError('Frozen splits required')
    for x in items:
        if set(x)!={'item_id','split','text','input_ids','read_position'}:raise ValueError('Public fields only')
        if not x['input_ids'] or x['read_position']!=len(x['input_ids'])-1:raise ValueError('Raw prefix endpoint')
        if any(type(t)is not int or t<0 for t in x['input_ids']):raise ValueError('Token IDs')
    return [dict(id=x['item_id'],ids=x['input_ids'],text=x['text'],split=x['split']) for x in items]

class NoFit(RuntimeError):pass
class Clock:
    def __init__(self,out,end):self.out,self.end,self.events=out,end,[]
    def check(self):
        if time.time()>=self.end-120:raise NoFit('Fixed deadline with retrieval reserve')
    def call(self,phase,fn,remaining_units=0):
        self.check();start=time.monotonic()
        try:v=fn()
        finally:
            self.events.append(dict(phase=phase,seconds=time.monotonic()-start));write(self.out/'PHASE_TIMINGS.json',self.events)
        self.check();return v
    def forecast(self,remaining):
        samples=[x['seconds'] for x in self.events if x['phase']=='capture']
        seconds=remaining*1.25*float(np.mean(samples));fits=time.time()+seconds<self.end-120
        write(self.out/'FORECAST.json',dict(remaining_batches=remaining,remaining_seconds=seconds,margin=1.25,mean_real_batch_seconds=float(np.mean(samples)),admitted=fits))
        if not fits:raise NoFit('Capture full inventory does not fit')

def acquire(items,backend,clock,out):
    backend.validate_tokenization(items)
    # Synthetic warmup is charged and discarded; real pilot is retained.
    dummy=dict(id='synthetic',ids=backend.oracle.tok.encode('A neutral synthetic warmup.',add_special_tokens=False))
    clock.call('warmup',lambda:backend.capture([dummy]))
    parts={42:[],44:[]};chunks=[items[i:i+8] for i in range(0,len(items),8)]
    (out/'batches').mkdir()
    for index,chunk in enumerate(chunks):
        values=clock.call('capture',lambda:backend.capture(chunk))
        for layer in parts:
            h=values[layer]
            if h.shape!=(len(chunk),5120) or h.dtype!=np.float32 or not np.isfinite(h).all():raise ValueError('Finite raw residual grid')
            parts[layer].append(h)
            np.save(out/'batches'/f'{index:04d}.{layer}.npy',h,allow_pickle=False)
        write(out/'PROGRESS.json',dict(completed_items=min((index+1)*8,len(items)),total_items=len(items)))
        clock.forecast(len(chunks)-index-1)
    for layer,v in parts.items():np.save(out/f'acts{layer}.npy',np.concatenate(v),allow_pickle=False)
    write(out/'items.order.json',[x['id'] for x in items])
    for layer in parts:
        h=np.load(out/f'acts{layer}.npy',allow_pickle=False)
        if h.shape!=(6720,5120) or not np.isfinite(h).all():raise ValueError('Complete capture required')

def main():
    sys.path.insert(0,str(ROOT))
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e49/job'))
    sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e49/job/vendor'))
    if sys.argv[1:]==['--cpu-import-preflight']:
        from e36_worker import NativeBackend
        import parity_gate
        from projects.g_agreement.blindspot import run
        from mats.capture import capture
        from mats.readers.olens import load_olens
        print('SCRIPT_ENTRY_IMPORT_PREFLIGHT_PASS_NO_MODEL_LOAD')
        return
    p=argparse.ArgumentParser()
    for k in ['inputs','assets','assignment','out','source-seal']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--source-sha',required=True);a=p.parse_args()
    if sha(a.source_seal)!=a.source_sha:raise ValueError('Source seal')
    source=json.loads(a.source_seal.read_text())
    for n,h in source['files'].items():
        path=(ROOT/n).resolve()
        if not path.is_relative_to(ROOT) or sha(path)!=h:raise ValueError('Source member '+n)
    if sha(a.inputs/'PUBLIC_ITEMS.jsonl')!=PUBLIC_SHA:raise ValueError('Exact v2 items')
    items=validate([json.loads(x) for x in (a.inputs/'PUBLIC_ITEMS.jsonl').read_text().splitlines()])
    ass=json.loads(a.assignment.read_text())
    if (ass['experiment']!='E97_CAPTURE_V2' or ass['gpu_count']!=1 or ass['cap_seconds']!=2700
        or ass['daily_budget_verified'] is not True or ass['absolute_deadline_epoch']>ass['pod_created_epoch']+3240
        or ass['pod_id']!=os.environ.get('RUNPOD_POD_ID') or sha(a.assets)!=ass['assets']['sha256']):raise ValueError('Assignment/identity/budget')
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass)
    clock=Clock(a.out,ass['absolute_deadline_epoch']);clock.check()
    timer=threading.Timer(max(0,clock.end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    status='FAILED'
    try:
        sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
        sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e49/job'))
        sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e49/job/vendor'))
        from e36_worker import NativeBackend
        import parity_gate
        backend=NativeBackend(ROOT,a.assets,{'gpu_type':'H200'})
        import torch
        torch.manual_seed(20261028);np.random.seed(20261028)
        clock.call('oracle_setup',backend.load_oracle)
        parity=a.out/'parity';parity.mkdir()
        binding=dict(path=str(a.inputs/'parity/INPUT_SEAL.json'),sha256=parity_gate.INPUT_SHA256)
        parity_gate.run_gate(backend,clock,parity,parity_gate.load_inputs(binding))
        write(a.out/'CAPTURE_STARTED.json',dict(utc=datetime.now(timezone.utc).isoformat(),epoch=time.time()))
        acquire(items,backend,clock,a.out);status='COMPLETE'
    except BaseException as e:
        status='NO_FIT' if isinstance(e,NoFit) else 'FAILED'
        write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:300]));raise
    finally:
        timer.cancel()
        first=a.out/'parity/PARITY_RESULT.json'
        write(a.out/'CAPTURE_SEAL.json',dict(experiment='E97',version=2,status=status,bank_seal_sha256=BANK_SHA,
            public_items_sha256=PUBLIC_SHA,source_seal_sha256=a.source_sha,pod_id=ass['pod_id'],
            completed_utc=datetime.now(timezone.utc).isoformat(),reader_outputs=0,reader_outputs_opened=False,
            first_output_utc=datetime.fromtimestamp(first.stat().st_mtime,timezone.utc).isoformat() if first.exists() else 'unknown',
            first_output_evidence=dict(source='archived_file_mtime',path='parity/PARITY_RESULT.json',scope='preproduction validation analysis',mtime_ns=first.stat().st_mtime_ns) if first.exists() else dict(reason='No readout, judgment or analysis output'),
            files={str(q.relative_to(a.out)):sha(q) for q in sorted(a.out.rglob('*')) if q.is_file() and q.name!='CAPTURE_SEAL.json'}))
if __name__=='__main__':main()
