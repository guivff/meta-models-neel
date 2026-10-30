"""E97 v2 capture only. No production reader entry point or GO handling."""
from pathlib import Path
import argparse, hashlib, json, os, signal, sys, threading, time, ast, types
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
    parts={42:[]};chunks=[items[i:i+8] for i in range(0,len(items),8)]
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


def capture42_method():
    path=ROOT/'results/g_agreement/understand/e49/job/vendor/e36_worker.py'
    if sha(path)!='0732fdc76f788c0b1ff650381881eb2240bd897e97328b88ac699940bc8c391e':raise ValueError('Original capture backend pin')
    tree=ast.parse(path.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='NativeBackend')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='capture')
    class Only42(ast.NodeTransformer):
        changed=0
        def visit_List(self,node):
            if all(isinstance(x,ast.Constant)for x in node.elts)and [x.value for x in node.elts]==[42,44]:
                self.changed+=1;return ast.copy_location(ast.List(elts=[ast.Constant(42)],ctx=ast.Load()),node)
            return self.generic_visit(node)
        def visit_Tuple(self,node):
            if all(isinstance(x,ast.Constant)for x in node.elts)and [x.value for x in node.elts]==[42,44]:
                self.changed+=1;return ast.copy_location(ast.Tuple(elts=[ast.Constant(42)],ctx=ast.Load()),node)
            return self.generic_visit(node)
    transform=Only42();fn=transform.visit(fn)
    if transform.changed!=2:raise ValueError('Exact block-list-only capture change')
    import e36_worker
    scope=dict(vars(e36_worker));exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(path)+':42-only','exec'),scope)
    return scope['capture']


def load_b200(self):
    import torch
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1 or 'B200'not in torch.cuda.get_device_name(0):raise ValueError('Assigned single B200 required')
    from projects.g_agreement.blindspot import run as operational
    assets=operational._assets(self.assets_path,names=('model','olens'))
    self.oracle=operational._load_oracle(assets)

def hardware_smoke(backend,inputs,out):
    import torch
    sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e56/job'))
    from worker56 import Backend
    ref=json.loads((inputs/'SMOKE_REFERENCE.json').read_text());h=np.load(inputs/'SMOKE44.npy',allow_pickle=False)
    if h.shape!=(3,5120)or not np.isfinite(h).all()or len(ref['records'])!=3:raise ValueError('Three frozen H200 smoke items')
    seen=[]
    def finite_hook(module,args,value):
        if not torch.isfinite(value).all():raise ValueError('B200 nonfinite output')
        seen.append(True)
    hook=backend.oracle.model.get_output_embeddings().register_forward_hook(finite_hook)
    try:groups=Backend.native_one(backend,'oracle',h)
    finally:hook.remove()
    if len(groups)!=3 or any(len(g)!=1 for g in groups)or not seen:raise ValueError('B200 finite three-item smoke failed')
    comparisons=[]
    for expected,group in zip(ref['records'],groups):
        actual=group[0]['raw'];old=expected['raw'];at=next((i for i,(a,b)in enumerate(zip(old,actual))if a!=b),min(len(old),len(actual)))if old!=actual else None
        comparisons.append(dict(id=expected['id'],exact_match=old==actual,first_divergence_character=at,H200_raw=old,B200_raw=actual))
    write(out/'B200_SMOKE.json',dict(status='PASS',loads=True,finite_logits=True,items=3,hardware_note='cb76843c',reference_seal_sha256=ref['source_reader_seal_sha256'],reference_batch=ref['reference_batch'],smoke_batch=3,batch_context_may_also_affect_byte_parity=True,first_divergence=next((dict(item=x['id'],character=x['first_divergence_character'])for x in comparisons if not x['exact_match']),None),comparisons=comparisons))

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
        capture42_method()
        print('CAPTURE42_SCRIPT_IMPORT_PASS_NO_MODEL_LOAD')
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
    if (ass['experiment']!='E97_CAPTURE42_V2' or ass['gpu_count']!=1 or ass['cap_seconds']!=1651
        or ass['daily_budget_verified'] is not True or ass['absolute_deadline_epoch']>ass['pod_created_epoch']+1651
        or ass.get('gpu_type') not in ('H200','B200') or ass['pod_id']!=os.environ.get('RUNPOD_POD_ID') or sha(a.assets)!=ass['assets']['sha256']):raise ValueError('Assignment/identity/budget')
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
        backend=NativeBackend(ROOT,a.assets,{'gpu_type':ass['gpu_type']})
        if ass['gpu_type']=='B200':backend.load_oracle=types.MethodType(load_b200,backend)
        backend.capture=types.MethodType(capture42_method(),backend)
        import torch
        torch.manual_seed(20261028);np.random.seed(20261028)
        clock.call('oracle_setup',backend.load_oracle)
        if ass['gpu_type']=='B200':clock.call('B200_three_item_smoke',lambda:hardware_smoke(backend,a.inputs,a.out))
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
        candidates=[q for q in [a.out/'B200_SMOKE.json',a.out/'parity/PARITY_RESULT.json'] if q.exists()]
        first=min(candidates,key=lambda q:q.stat().st_mtime_ns) if candidates else a.out/'parity/PARITY_RESULT.json'
        write(a.out/'CAPTURE_SEAL.json',dict(experiment='E97',version=2,status=status,gpu_type=ass['gpu_type'],sites=[42],capture_items=6720,operational_ruling='5ad0c3ce',bank_seal_sha256=BANK_SHA,
            original_capture_seal_sha256='5dffccebc3cde76dda77ef089375f0b8489a362cd3819420e21bbbd2c8c32829',
            original_block44_sha256='e1447c98cc534328dd98fdc19743a841de9849c8db3013477f26a3b627becce2',retained_oracle_test44_sha256='113acaaeb7b292d283dfe91ee12a480b7e5b29f74dab35666211ea8c91756bee',
            forecast_sha256='5f099f9d84246fc4039e4f793844b67de498aedf368645af95d7f4bbcff23485',
            public_items_sha256=PUBLIC_SHA,source_seal_sha256=a.source_sha,pod_id=ass['pod_id'],
            completed_utc=datetime.now(timezone.utc).isoformat(),reader_outputs=0,reader_outputs_opened=False,
            first_output_utc=datetime.fromtimestamp(first.stat().st_mtime,timezone.utc).isoformat() if first.exists() else 'unknown',
            first_output_evidence=dict(source='archived_file_mtime',path=str(first.relative_to(a.out)),scope='hardware smoke or preproduction validation; no E97 reader outcome',mtime_ns=first.stat().st_mtime_ns) if first.exists() else dict(reason='No readout, judgment or analysis output'),
            files={str(q.relative_to(a.out)):sha(q) for q in sorted(a.out.rglob('*')) if q.is_file() and q.name!='CAPTURE_SEAL.json'}))
if __name__=='__main__':main()
