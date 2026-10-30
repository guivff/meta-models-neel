"""E97 reader-only phase; consumes frozen test activations after committed forecast GO."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, re, signal, sys, threading, time, types
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
CAPTURE='5dffccebc3cde76dda77ef089375f0b8489a362cd3819420e21bbbd2c8c32829'
BANK='2afa89f0e551274b82368075338f7b117dcbbe97b403bf4a29d0a6b442ea4f08'
FORECAST='5f099f9d84246fc4039e4f793844b67de498aedf368645af95d7f4bbcff23485'
FORECAST_COMMIT='8e8c0107d85b95bd7d9e93a9fe8752ff0a4627f4'
CAPS={'oracle':6500,'nla':11500}
RECAPTURE_SOURCE='ea3610f5a56a0b59e98ea634f391edd945393e99aa75c669d650bdc8b48fa355'
FALLBACK_EPOCH=datetime(2026,10,29,17,tzinfo=timezone.utc).timestamp()

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n');os.replace(tmp,p)
def verify(root,name,digest):
    p=root/name
    if sha(p)!=digest:raise ValueError('Seal digest')
    s=json.loads(p.read_text())
    for n,h in s['files'].items():
        q=(root/n).resolve()
        if not q.is_relative_to(root.resolve()) or sha(q)!=h:raise ValueError('Sealed member '+n)
    return s

def imports():
    sys.path[:0]=[str(ROOT),str(ROOT/'external/mats-nla-workspace/src'),str(ROOT/'results/g_agreement/understand/e56/job')]
    from worker56 import Backend
    import parity_gate
    return Backend,parity_gate

def validate(items,vectors):
    if len(items)!=3360 or len({x['id'] for x in items})!=3360:raise ValueError('Exact3360testIDs')
    if vectors.shape!=(3360,5120) or vectors.dtype!=np.float32 or not np.isfinite(vectors).all():raise ValueError('Test vectors')
    for i,x in enumerate(items):
        if set(x)!={'id','vector_index'} or x['vector_index']!=i or not re.fullmatch('[0-9a-f]{24}',x['id']):raise ValueError('Opaque test grid only')

def validate_go(go,inputs,reader,now):
    if (go.get('experiment')!='E97' or go.get('capture_sha256')!=CAPTURE or go.get('bank_sha256')!=BANK
        or go.get('forecast_sha256')!=FORECAST or go.get('forecast_original_commit')!=FORECAST_COMMIT
        or go.get('forecast_git_verified') is not True or go.get('input_sha256_by_reader',{}).get(reader)!=inputs
        or not go.get('forecast_commit_epoch',float('inf'))<go.get('issued_epoch',0)<=now
        or go.get('forecast_published_before_GO') is not True):raise ValueError('Committed forecast and exact-input GO required')
    if go.get('oracle_only_deadline_fallback') is True:
        if reader!='oracle' or go['issued_epoch']<FALLBACK_EPOCH:raise ValueError('Oracle-only fallback requires missed Thu18CET deadline')
    elif (not re.fullmatch('[0-9a-f]{64}',go.get('block42_recapture_sha256',''))
          or go.get('recapture_git_verified') is not True or go.get('recapture_published_before_GO') is not True
          or not re.fullmatch('[0-9a-f]{40}',go.get('recapture_shared_commit',''))
          or not go.get('recapture_sealed_epoch',float('inf'))<go['issued_epoch']):raise ValueError('Published block42 recapture seal before GO required')

def verify_recapture_binding(root,inputs,go,reader):
    if go.get('oracle_only_deadline_fallback') is True:
        if reader!='oracle':raise ValueError('No NLA deadline fallback')
        return
    name='BLOCK42_RECAPTURE_SEAL.json';digest=go['block42_recapture_sha256']
    if inputs['files'].get(name)!=digest or sha(root/name)!=digest:raise ValueError('Exact recapture seal must be in sealed reader inputs')
    recap=json.loads((root/name).read_text())
    expected=dict(status='COMPLETE',sites=[42],capture_items=6720,operational_ruling='5ad0c3ce',bank_seal_sha256=BANK,
        original_capture_seal_sha256=CAPTURE,forecast_sha256=FORECAST,source_seal_sha256=RECAPTURE_SOURCE,
        public_items_sha256='22a5870f5ab41e520787b88c79dab3af463bfb36461edeea518bc2501488a6ef',
        original_block44_sha256='e1447c98cc534328dd98fdc19743a841de9849c8db3013477f26a3b627becce2',
        retained_oracle_test44_sha256='113acaaeb7b292d283dfe91ee12a480b7e5b29f74dab35666211ea8c91756bee',reader_outputs=0)
    if any(recap.get(k)!=v for k,v in expected.items()):raise ValueError('Registered complete block42-only recapture binding')
    completed=datetime.fromisoformat(recap['completed_utc'].replace('Z','+00:00')).timestamp()
    if completed>go['recapture_sealed_epoch'] or recap.get('gpu_type')not in ('H200','B200'):raise ValueError('Recapture ordering/hardware')
    if not re.fullmatch('[0-9a-f]{64}',recap.get('files',{}).get('acts42.npy','')):raise ValueError('Sealed block42 aggregate required')
    if reader=='nla' and inputs.get('block42_vector_source_sha256')!=recap['files']['acts42.npy']:raise ValueError('NLA vectors must derive from exact new42 aggregate')

def first_output_info(out):
    candidates=list((out/'records').glob('*.json'))+list(out.glob('B200_SMOKE*.json'))+[p for p in [out/'parity/PARITY_RESULT.json'] if p.exists()]
    if not candidates:return 'unknown',dict(reason='No readout or validation analysis written')
    first=min(candidates,key=lambda p:p.stat().st_mtime_ns)
    scope='first production greedy readout' if first.parent.name=='records' else 'preproduction hardware smoke or parity validation analysis'
    return datetime.fromtimestamp(first.stat().st_mtime,timezone.utc).isoformat(),dict(source='archived_file_mtime',path=str(first.relative_to(out)),mtime_ns=first.stat().st_mtime_ns,scope=scope)

class NoFit(RuntimeError):pass
class Clock:
    def __init__(self,out,end):self.out,self.end,self.events,self.samples=out,end,[],[]
    def check(self):
        if time.time()>=self.end-120:raise NoFit('Fixed custody retrieval reserve')
    def call(self,phase,fn,remaining_units=0):
        self.check();start=time.monotonic()
        try:value=fn()
        finally:
            dt=time.monotonic()-start;self.events.append(dict(phase=phase,seconds=dt));write(self.out/'PHASE_TIMINGS.json',self.events)
        if phase=='native':self.samples.append(dt)
        self.check();return value
    def forecast(self,remaining):
        seconds=1.25*remaining*float(np.mean(self.samples));fits=time.time()+seconds<self.end-120
        write(self.out/'FORECAST.json',dict(remaining_batches=remaining,remaining_seconds=seconds,margin=1.25,mean_real_seconds=float(np.mean(self.samples)),admitted=fits))
        if not fits:raise NoFit('Remaining native grid does not fit')

def acquire(items,vectors,reader,backend,clock,out):
    clock.call('synthetic_warmup',lambda:backend.native_one(reader,np.random.default_rng(20261028).normal(size=(8,5120)).astype(np.float32)))
    (out/'records').mkdir();jobs=[(items[i:i+8],vectors[i:i+8]) for i in range(0,len(items),8)]
    for index,(units,h) in enumerate(jobs):
        values=clock.call('native',lambda:backend.native_one(reader,h))
        if len(values)!=len(units) or any(len(group)!=1 for group in values):raise ValueError('One greedy result per item')
        for unit,group in zip(units,values):
            write(out/'records'/(unit['id']+'.json'),dict(id=unit['id'],reader=reader,repeat=0,reader_native_layer=44 if reader=='oracle' else 42,**group[0]))
        write(out/'PROGRESS.json',dict(completed_items=min((index+1)*8,len(items)),total_items=len(items)))
        clock.forecast(len(jobs)-index-1)
    if {p.stem for p in (out/'records').glob('*.json')}!={x['id'] for x in items}:raise ValueError('Complete inventory required')

def main():
    if sys.argv[1:]==['--cpu-import-preflight']:
        imports();from projects.g_agreement.blindspot import run
        from mats.readers.nla import load_nla
        print('READER_SCRIPT_IMPORT_PASS_NO_MODEL_LOAD');return
    p=argparse.ArgumentParser()
    for k in ['inputs','assets','assignment','go','out','source-seal']:p.add_argument('--'+k,type=Path,required=True)
    for k in ['source-sha','input-sha']:p.add_argument('--'+k,required=True)
    a=p.parse_args();verify(ROOT,str(a.source_seal.relative_to(ROOT)),a.source_sha)
    inputs=verify(a.inputs,'INPUT_SEAL.json',a.input_sha);reader=inputs['reader']
    if reader not in CAPS or inputs['capture_sha256']!=CAPTURE or inputs['bank_sha256']!=BANK or inputs['n']!=3360 or inputs['test_only']is not True:raise ValueError('Frozen capture/test binding')
    items=json.loads((a.inputs/'items.json').read_text());h=np.load(a.inputs/'vectors.npy',allow_pickle=False);validate(items,h)
    go=json.loads(a.go.read_text());validate_go(go,a.input_sha,reader,time.time());verify_recapture_binding(a.inputs,inputs,go,reader);ass=json.loads(a.assignment.read_text())
    if (ass['experiment']!='E97' or ass['reader']!=reader or ass['cap_seconds']!=CAPS[reader] or ass['gpu_count']!=1 or ass.get('gpu_type')not in ('H200','B200')
        or ass['pod_id']!=os.environ.get('RUNPOD_POD_ID') or ass['daily_budget_verified']is not True
        or ass['absolute_deadline_epoch']>ass['pod_created_epoch']+CAPS[reader]+900
        or sha(a.assets)!=ass['assets']['sha256']):raise ValueError('Budget/custody/asset identity')
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);write(a.out/'GO_RECEIPT.json',go)
    clock=Clock(a.out,ass['absolute_deadline_epoch']);clock.check();timer=threading.Timer(max(0,clock.end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='FAILED'
    try:
        Backend,parity_gate=imports();b=Backend(ROOT,a.assets,{'gpu_type':ass['gpu_type']})
        if ass['gpu_type']=='B200':
            from projects.g_agreement.e97.hardware import load_b200,smoke
            b.load_oracle=types.MethodType(load_b200,b)
        import torch
        torch.manual_seed(20261028);np.random.seed(20261028)
        clock.call('oracle_setup',b.load_oracle)
        if ass['gpu_type']=='B200':clock.call('B200_oracle_smoke',lambda:smoke(b,'oracle',a.inputs,a.out,write))
        par=a.out/'parity';par.mkdir()
        parity_gate.run_gate(b,clock,par,parity_gate.load_inputs(dict(path=str(a.inputs/'parity/INPUT_SEAL.json'),sha256=parity_gate.INPUT_SHA256)))
        if reader=='nla':
            clock.call('nla_setup',b.load_nla)
            if ass['gpu_type']=='B200':clock.call('B200_nla_smoke',lambda:smoke(b,'nla',a.inputs,a.out,write))
        acquire(items,h,reader,b,clock,a.out);status='COMPLETE'
    except BaseException as e:
        status='NO_FIT' if isinstance(e,NoFit) else 'FAILED';write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:300]));raise
    finally:
        timer.cancel();first_utc,first_evidence=first_output_info(a.out)
        write(a.out/'OUTPUT_SEAL.json',dict(experiment='E97',reader=reader,gpu_type=ass['gpu_type'],status=status,input_sha256=a.input_sha,source_sha256=a.source_sha,capture_sha256=CAPTURE,forecast_sha256=FORECAST,go_sha256=sha(a.go),first_output_utc=first_utc,first_output_evidence=first_evidence,reader_outputs_opened=False,completed_utc=datetime.now(timezone.utc).isoformat(),files={str(q.relative_to(a.out)):sha(q)for q in sorted(a.out.rglob('*'))if q.is_file()and q.name!='OUTPUT_SEAL.json'}))
if __name__=='__main__':main()
