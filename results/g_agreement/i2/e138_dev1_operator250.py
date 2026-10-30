import argparse, hashlib, json, os, signal, threading, time
from datetime import datetime, timezone
from pathlib import Path

def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p, x):
    p = Path(p);p.parent.mkdir(parents=True, exist_ok=True);q = p.with_suffix('.new');q.write_text(json.dumps(x, indent=2)+'\n');q.replace(p)
def verify(root, name, digest):
    p = Path(root)/name;assert sha(p) == digest, 'seal '+name
    d = read(p)
    for n, h in d['files'].items(): assert sha(Path(root)/n) == h, 'member '+n
    return d
def forecast(created, deadline, now, remaining, observed):
    """I-2 operator a3f1b621 rule, unchanged."""
    assert now >= created and all(n >= 0 for n in remaining.values())
    assert all(not n or observed.get(k) for k, n in remaining.items()), 'ALL_PENDING_PHASES_REQUIRE_MEASURED_PILOT'
    need = 1.25*(now-created+sum(n*max(observed[k]) for k, n in remaining.items() if n))+60
    return dict(status='ADMIT' if created+need <= deadline else 'NO_FIT', projected_total_cap_seconds=need, elapsed=now-created, remaining_calls=remaining,
                max_observed_seconds={k: max(v) for k, v in observed.items() if v}, margin=1.25, reserve_seconds=60, original_deadline=deadline)
class Custody:
    def __init__(self, a, out): self.a = a;self.out = out;self.events = [];self.observed = {'capture':[31.899021986988373], 'oracle_setup':[196.58878472691868], 'native':[42.705082369968295]}
    def call(self, phase, f, measured=False):
        assert time.time() < self.a['absolute_deadline_epoch']-60, 'NO_FIT_ABSOLUTE_RESERVE'
        t = time.monotonic();v = f()
        import torch
        torch.cuda.synchronize();dt = time.monotonic()-t;self.events.append(dict(phase=phase, seconds=dt));write(self.out/'TIMINGS.json', self.events)
        if measured: self.observed.setdefault(phase, []).append(dt)
        return v
    def fit(self, remaining):
        f = forecast(self.a['pod_created_epoch'], self.a['absolute_deadline_epoch'], time.time(), remaining, self.observed);write(self.out/'FORECAST.json', f);return f['status'] == 'ADMIT'

LAYERS=(44,)
def run(xs,vectors,assets,out,c):
    import numpy as np
    from projects.g_agreement.e101.runner import dependencies
    from projects.g_agreement.e138 import runner
    rt=dependencies()[1](assets)
    if not c.fit(dict(oracle_setup=1,native=21)):return 'NO_FIT'
    c.call('oracle_setup',rt.load_oracle,True)
    jobs=list(runner.batches(xs,size=8));assert len(jobs)==21 and sum(len(j)for j in jobs)==168
    for k,job in enumerate(jobs):
        if not c.fit(dict(native=len(jobs)-k)):return 'NO_FIT'
        ix=[x['vector_index']for x in job];v=vectors[ix].copy();before=v.tobytes()
        rr=c.call('native',lambda:runner.oracle_batch(rt,v,44),True)
        assert len(rr)==len(job) and v.tobytes()==before
        write(out/f'jobs/{k:06d}.json',[dict(z,id=x['id']+':oracle:44',item_id=x['id'],source_layer=44,reader='oracle',gpu_type='H200')for x,z in zip(job,rr)])
        write(out/'PROGRESS.json',dict(completed=sum(len(j)for j in jobs[:k+1]),planned=168))
    return 'COMPLETE'

def main():
    p = argparse.ArgumentParser()
    for n in ('inputs', 'assets', 'assignment', 'source-seal', 'out'): p.add_argument('--'+n, type=Path, required=True)
    for n in ('source-sha', 'input-sha'): p.add_argument('--'+n, required=True)
    p.add_argument('--validate-only', action='store_true');a = p.parse_args()
    verify(Path.cwd(), str(a.source_seal), a.source_sha)
    from projects.g_agreement.e138 import runner
    xs,vectors,manifest=runner.load(a.inputs,a.input_sha);assert len(xs)==168 and vectors.shape==(168,5120)
    from projects.g_agreement.e101.runner import dependencies  # every module run() needs, imported before any assignment or model
    from projects.g_agreement.e101 import runner109
    from mats.readers.olens import TRAINED_LAYERS
    assert callable(dependencies) and callable(runner.oracle_batch) and callable(runner109.backend87) and set(LAYERS) <= set(TRAINED_LAYERS)
    if a.validate_only: print('VALIDATE_OK', len(xs), sum(len(j) for j in runner.batches(xs, 8)), len(xs));return
    ass = read(a.assignment)
    assert ass['experiment'] == 'E138' and ass['pod_id'] == os.environ.get('RUNPOD_POD_ID') and ass['gpu_type'] == 'H200' and ass['allocation_verified'] and ass['daily_budget_verified']
    assert ass['source_sha256'] == a.source_sha and ass['input_sha256'] == a.input_sha and ass['assets_sha256'] == sha(a.assets)
    assert ass['cap_seconds']==2066 and ass['cap_seconds']<=3600 and ass['absolute_deadline_epoch'] == min(ass['pod_created_epoch']+ass['cap_seconds'],1793364600) and ass['pod_created_epoch'] < 1793354400 and ass['cap_seconds']*5.29/3600 <= 25
    import torch  # inline single-H200 check (as I-2's e123_native233); e100.worker is not in C's E126 source archive
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1 and 'H200' in torch.cuda.get_device_name(0), 'one H200'
    a.out.mkdir(parents=True, exist_ok=False);write(a.out/'ASSIGNMENT.json', ass);write(a.out/'INVENTORY.json', dict(ids=[x['id'] for x in xs], source_sha256=a.source_sha, input_sha256=a.input_sha))
    c = Custody(ass, a.out);status = 'FAILED'
    timer = threading.Timer(max(0, ass['absolute_deadline_epoch']-time.time()-30), lambda: os.kill(os.getpid(), signal.SIGKILL));timer.daemon = True;timer.start()
    try: status = run(xs, vectors, a.assets, a.out, c)
    except BaseException as e: write(a.out/'FAILURE.json', dict(type=type(e).__name__, message=str(e)[:400]));raise
    finally:
        timer.cancel();files = [q for q in a.out.rglob('*') if q.is_file() and q.name != 'OUTPUT_SEAL.json'];real = [q for q in files if q.parent.name in ('jobs', 'capture', 'answers')]
        first = min(real, key=lambda q: q.stat().st_mtime_ns) if real else None
        write(a.out/'OUTPUT_SEAL.json', dict(experiment='E138', status=status, source_sha256=a.source_sha, input_sha256=a.input_sha, labels_cpu_only=True, judging=False, reader_calls=0, outputs_unopened=True,
              first_output_utc=datetime.fromtimestamp(first.stat().st_mtime, timezone.utc).isoformat() if first else 'unknown',
              first_output_evidence=dict(member=str(first.relative_to(a.out)), sha256=sha(first)) if first else None, files={str(q.relative_to(a.out)): sha(q) for q in files}))
if __name__ == '__main__': main()
