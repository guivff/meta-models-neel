"""Native-only E79 extension: reuse frozen original acquisition and Clock."""
from pathlib import Path
from datetime import datetime, timezone
import argparse,ast,hashlib,importlib.util,json,os,sys,threading,signal,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
ORIGINAL_SHA='721ce7680400df9a96b0ce1e54ea944a5c080acd94335bed08006d790a9a8f0c'
INPUT_SHA='dc70e8ba11e7cff43d19fe91c6c02c15ad20749fa2aa56aeca69317d3ecab97c'
ROWS={'user_expertise','unit_system'}
FIELDS={'id','index','row','arm','condition','alpha','block'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    p=Path(p);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n');os.replace(t,p)
def verify(root,name,digest):
    p=root/name
    if sha(p)!=digest:raise ValueError('Seal identity')
    s=json.loads(p.read_text())
    for n,h in s['files'].items():
        f=(root/n).resolve()
        if not f.is_relative_to(root.resolve())or sha(f)!=h:raise ValueError('Member identity')
    return s

def validate(items,h):
    if len(items)!=2688 or len({x['id']for x in items})!=2688 or h.shape!=(2688,5120)or h.dtype!=np.float32 or not np.isfinite(h).all():raise ValueError('Exact2688finite fp32 owner vectors')
    if any(set(x)!=FIELDS or x['arm']!='A' or x['block']!=44 or x['index']!=i for i,x in enumerate(items)):raise ValueError('Owner public schema only')
    cells={('baseline',0)}|{(d,a)for d in ['J','nonJ','random']for a in [.25,.5,1,2,4]}
    if {x['row']for x in items}!=ROWS:raise ValueError('New states only')
    for row in ROWS:
        group=[x for x in items if x['row']==row]
        if {(x['condition'],x['alpha'])for x in group}!=cells:raise ValueError('Frozen16cell grid')
        if any(sum((x['condition'],x['alpha'])==c for x in group)!=84 for c in cells):raise ValueError('84items percell')
    return [dict(id=x['id'],arm='A',vector_index=x['index'],feature=x['row'])for x in items]

def original():
    sys.path[:0]=[str(ROOT),str(ROOT/'external/mats-nla-workspace/src')]
    path=ROOT/'results/g_agreement/understand/e79/worker.py'
    if sha(path)!=ORIGINAL_SHA:raise ValueError('Original runner pin')
    spec=importlib.util.spec_from_file_location('_frozen_e79_runner',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    tree=ast.parse(path.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='acquire');kept=[];removed=0;changed=0
    for n in fn.body:
        is_token=isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='token'for t in n.targets)
        is_function=isinstance(n,ast.FunctionDef)and n.name=='warm_cont'
        is_call=isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)and n.value.args and isinstance(n.value.args[0],ast.Constant)and n.value.args[0].value=='continuation_warmup_discarded'
        if is_token or is_function or is_call:removed+=1;continue
        if isinstance(n,ast.For)and isinstance(n.target,ast.Name)and n.target.id=='kind':
            if ast.literal_eval(n.iter)!=('native','continuation'):raise ValueError('Original pilot contract')
            n.iter=ast.Tuple(elts=[ast.Constant(value='native')],ctx=ast.Load());changed+=1
        kept.append(n)
    if removed!=3 or changed!=1:raise ValueError('Unexpected acquisition delta')
    fn.body=kept;scope=dict(vars(module));exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(path)+':A-only', 'exec'),scope)
    return module,scope['acquire']

def main():
    if sys.argv[1:]==['--cpu-import-preflight']:
        original();from projects.g_agreement.blindspot import run
        print('E79_EXTENSION_EXACT_IMPORT_PASS_NO_MODEL_LOAD');return
    p=argparse.ArgumentParser()
    for n in ['inputs','assignment','assets','out','source-seal']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--source-sha',required=True);p.add_argument('--hardware-reference',type=Path);a=p.parse_args();verify(ROOT,str(a.source_seal.relative_to(ROOT)),a.source_sha)
    inp=verify(a.inputs,'RESULT_SEAL.json',INPUT_SHA)
    if inp['experiment']!='E79_extension'or inp['status']!='SEALED_INPUTS_NO_READERS':raise ValueError('Owner extension seal')
    items=validate(json.loads((a.inputs/'ITEMS.json').read_text()),h:=np.load(a.inputs/'INPUT_VECTORS.npy',allow_pickle=False))
    ass=json.loads(a.assignment.read_text())
    if (ass['experiment']!='E79ext'or ass['gpu_count']!=1 or ass['cap_seconds']!=7200
        or ass['absolute_deadline_epoch']!=ass['pod_created_epoch']+7200 or ass['daily_budget_verified']is not True
        or ass['pod_id']!=os.environ.get('RUNPOD_POD_ID')or sha(a.assets)!=ass['assets']['sha256']):raise ValueError('Fixed creation budget and provider identity')
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);status='FAILED';timer=threading.Timer(max(0,ass['absolute_deadline_epoch']-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    try:
        module,acquire=original()
        import torch
        torch.manual_seed(20261028);np.random.seed(20261028)
        # Original Clock/native loop unchanged; reserve120s in addition to its60s.
        from projects.g_agreement.e79_extension.hardware import backend
        bound=backend(module,ROOT,a.assets,ass,a.hardware_reference,a.out,write)
        complete=acquire(items,h,bound,module.Clock(a.out,ass['absolute_deadline_epoch']-120),a.out)
        if complete:
            jobs=json.loads((a.out/'JOB_GRID.json').read_text());done=json.loads((a.out/'COMPLETED.json').read_text())
            if len(jobs)!=336 or done!=list(range(336))or any(x['kind']!='native'for x in jobs):raise ValueError('Full extension native inventory')
        status='COMPLETE'if complete else'NO_FIT'
    except BaseException as e:status='FAILED';write(a.out/'FAILURE.json',dict(type=type(e).__name__,message=str(e)[:300]));raise
    finally:
        timer.cancel();files=list((a.out/'jobs').glob('*.json'))+list(a.out.glob('B200_SMOKE.*.json'));first=min(files,key=lambda p:p.stat().st_mtime_ns)if files else None
        write(a.out/'OUTPUT_SEAL.json',dict(experiment='E79_extension',status=status,gpu_type=ass.get('gpu_type','unknown'),input_seal_sha256=INPUT_SHA,source_seal_sha256=a.source_sha,pod_id=ass['pod_id'],states=sorted(ROWS),native_max_new_tokens=128,first_output_utc=datetime.fromtimestamp(first.stat().st_mtime,timezone.utc).isoformat()if first else'unknown',first_output_evidence=dict(source='archived_file_mtime',path=str(first.relative_to(a.out)),mtime_ns=first.stat().st_mtime_ns,scope='hardware_smoke'if first.name.startswith('B200_SMOKE.')else'first_native_readout')if first else dict(reason='No real readout written'),outputs_opened=False,completed_utc=datetime.now(timezone.utc).isoformat(),files={str(p.relative_to(a.out)):sha(p)for p in sorted(a.out.rglob('*'))if p.is_file()and p.name!='OUTPUT_SEAL.json'}))
if __name__=='__main__':main()
