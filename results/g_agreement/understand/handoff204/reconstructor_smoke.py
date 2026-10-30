"""One sealed public item through both existing reconstruction APIs; no judging."""
import argparse
import gc
import hashlib
import json
import math
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'external/mats-nla-workspace/src'))

def read(p):
    return json.loads(Path(p).read_text())

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require(ok, msg):
    if not ok:
        raise ValueError(msg)

def save(p, x):
    p.write_text(json.dumps(x, indent=2)+'\n')

def check_input(item):
    require(set(item) == {'id', 'text'} and type(item['id']) is str and
            type(item['text']) is str and bool(item['text'].strip()), 'one public sealed item')

def check_vector(v):
    import numpy as np
    x = v.detach().float().cpu().numpy() if hasattr(v, 'detach') else np.asarray(v)
    require(x.shape == (1, 5120) and np.isfinite(x).all(), 'finite1x5120 reconstruction')
    return dict(shape=list(x.shape), finite=True, output_sha256=hashlib.sha256(x.tobytes()).hexdigest())

class Backend:
    def __init__(self, assets, official, whitener):
        self.assets = assets; self.official = official; self.whitener = whitener

    def oracle(self, text):
        import common
        from projects.g_agreement.blindspot.run import _assets
        from projects.g_agreement.blindspot.ar_tests import _assets as ar_assets
        from projects.g_agreement.w_claims.ar import load_reconstructor, reconstruct
        assets = _assets(self.assets, ('model',)); ar_assets(self.assets, ('ar',))
        ar, tok, _ = load_reconstructor(self.official, self.whitener, assets['ar'], assets['model'])
        ar.eval()
        return reconstruct(ar, tok, [text])

    def nla(self, text):
        from projects.g_agreement.understand.worker import load_decoder_only
        decoder = load_decoder_only(self.assets)
        return decoder.reconstruct([text], batch=1)

class StubBackend:
    def oracle(self, text):
        import torch
        # Tiny model output exercises the exact one-item result path on CPU.
        with torch.inference_mode():
            return torch.nn.Linear(2,5120,bias=False)(torch.ones(1,2))

    nla = oracle

def execute(item, backend, out, end, dry_run=False):
    check_input(item); out.mkdir(parents=True, exist_ok=False); phases=[]
    for name in ('oracle', 'nla'):
        require(time.time() < end, 'fixed1800s custody deadline')
        start = time.monotonic()
        try:
            result = check_vector(getattr(backend, name)(item['text']))
            require(time.time() < end, 'fixed1800s custody deadline')
            save(out/(name.upper()+'.json'), dict(status='CPU_STUB_ONLY' if dry_run else 'PASS',
                 item_id=item['id'], **result))
            phases.append(dict(reader=name, seconds=time.monotonic()-start, status='COMPLETE'))
        except BaseException as exc:
            phases.append(dict(reader=name, seconds=time.monotonic()-start, status='FAILED', error_type=type(exc).__name__))
            save(out/'PHASE_TIMINGS.json', phases)
            raise
        save(out/'PHASE_TIMINGS.json', phases)
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return dict(status='CPU_STUB_ONLY' if dry_run else 'BOTH_RECONSTRUCTORS_RUN',
        item_id=item['id'], readers=2, model_generation=0, judging=0, statistical_analysis=0)

def main():
    p=argparse.ArgumentParser()
    for name in ('assignment','assets','official','whitener','out'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--dry-run', action='store_true'); a=p.parse_args()
    request=read(HERE/'SMOKE_REQUEST.json')
    for name,digest in request['source_files'].items():
        require(sha(ROOT/name)==digest, 'source pin '+name)
    require(sha(HERE/'SMOKE_ITEM.json')==request['item_sha256'], 'item seal')
    assignment=read(a.assignment)
    require(assignment['experiment']=='E96_RECONSTRUCTOR_SMOKE' and assignment['gpu_count']==1
            and assignment['budget_verified'] is True, 'integrator assignment')
    cap=assignment['cap_seconds']; end=assignment['absolute_deadline_epoch']
    require(0<cap<=request['cap_seconds']<=1800 and
            end==assignment['custody_start_epoch']+cap and
            assignment['custody_start_epoch']<=time.time()<end, 'fixed custody cap')
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('hard deadline')))
    signal.setitimer(signal.ITIMER_REAL, max(.01,end-time.time()))
    backend=StubBackend() if a.dry_run else Backend(a.assets,a.official,a.whitener)
    result=execute(read(HERE/'SMOKE_ITEM.json'),backend,a.out,end,a.dry_run)
    result.update(assignment_sha256=sha(a.assignment),request_sha256=sha(HERE/'SMOKE_REQUEST.json'),
                  item_sha256=request['item_sha256'],completed_epoch=time.time())
    if not a.dry_run:
        result['assets_sha256']=sha(a.assets)
    result['files']={f.name:sha(f) for f in a.out.iterdir() if f.is_file()}
    save(a.out/'OUTPUT_SEAL.json', result)
    signal.setitimer(signal.ITIMER_REAL,0)
    print(result['status'])

if __name__=='__main__':
    main()
