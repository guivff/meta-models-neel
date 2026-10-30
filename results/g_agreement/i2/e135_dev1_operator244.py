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
    def __init__(self, a, out): self.a = a;self.out = out;self.events = [];self.observed = {'capture':[31.899021986988373], 'oracle_setup':[196.58878472691868], 'native':[20.131339331972413]}
    def call(self, phase, f, measured=False):
        assert time.time() < self.a['absolute_deadline_epoch']-60, 'NO_FIT_ABSOLUTE_RESERVE'
        t = time.monotonic();v = f()
        import torch
        torch.cuda.synchronize();dt = time.monotonic()-t;self.events.append(dict(phase=phase, seconds=dt));write(self.out/'TIMINGS.json', self.events)
        if measured: self.observed.setdefault(phase, []).append(dt)
        return v
    def fit(self, remaining):
        f = forecast(self.a['pod_created_epoch'], self.a['absolute_deadline_epoch'], time.time(), remaining, self.observed);write(self.out/'FORECAST.json', f);return f['status'] == 'ADMIT'

LAYERS = (44, 52)

def run(xs, deltas, assets, out, c):
    import gc, numpy as np, torch
    from projects.g_agreement.e101.runner import dependencies
    from projects.g_agreement.e101 import runner109 as primitive
    from projects.g_agreement.e135 import runner
    from mats.readers.olens import TRAINED_LAYERS
    assert set(LAYERS) <= set(TRAINED_LAYERS)
    rt = dependencies()[1](assets);c.call('base_setup', rt.load_base);model, tok, cm = rt.subject()
    jobs = list(runner.batches(xs, size=8));assert sum(len(j) for j in jobs) == 168;vectors = {L: np.full((len(xs), 5120), np.nan, np.float32) for L in LAYERS};index = []
    for k, job in enumerate(jobs):
        if not c.fit(dict(capture=len(jobs)-k, oracle_setup=1, native=42)): return 'NO_FIT'
        def call():
            with cm: return runner.capture_answer_batch(model, tok, job, deltas[[x['delta_index'] for x in job]].copy())
        r = c.call('capture', call, True);assert r['intervention_installed'] is True and r['write_block'] == 40 and len(r['answers']) == len(job)
        for L in LAYERS:
            v = np.asarray(r['captures'][L] if L in r['captures'] else r['captures'][str(L)], dtype=np.float32);assert v.shape == (len(job), 5120) and np.isfinite(v).all()
            m = f'capture/{k:06d}_{L}.npy';(out/'capture').mkdir(exist_ok=True);np.save(out/m, v, allow_pickle=False)
            for j, x in enumerate(job): vectors[L][x['delta_index']] = v[j];index.append(dict(id=x['id'], source_layer=L, member=m, vector_index=j))
        write(out/f'answers/{k:06d}.json', dict(answers=[dict(a, gpu_type='H200') for a in r['answers']], read_norms=r['read_norms'], injection_metrics=r['injection_metrics'], calibration=r['calibration'], ids=[x['id'] for x in job]))
    assert all(np.isfinite(v).all() for v in vectors.values());write(out/'CAPTURE_INDEX.json', index)
    for L, v in vectors.items(): np.save(out/f'CAPTURE_{L}.npy', v, allow_pickle=False)
    del model, cm;rt.model = rt.tok = None;gc.collect();torch.cuda.empty_cache()
    c.call('oracle_setup', rt.load_oracle);b87 = primitive.backend87()
    planned = [(L, list(range(k, min(k+8, len(xs))))) for L in LAYERS for k in range(0, len(xs), 8)];done = 0
    for k, (L, ix) in enumerate(planned):
        v = vectors[L][ix].copy();before = v.tobytes();rr = c.call('native', lambda: b87.sweep(rt, 'oracle', v, L), True);assert len(rr) == len(ix) and v.tobytes() == before
        write(out/f'jobs/{k:06d}.json', [dict(z, id=xs[i]['id']+':oracle:'+str(L), item_id=xs[i]['id'], base_id=xs[i]['base_id'], condition=xs[i]['condition'], alpha=xs[i]['alpha'], source_layer=L, reader='oracle', gpu_type='H200') for i, z in zip(ix, rr)])
        done += len(ix);write(out/'PROGRESS.json', dict(completed=done, planned=336))
        if k+1 < len(planned) and not c.fit(dict(native=len(planned)-k-1)): return 'NO_FIT'
    return 'COMPLETE'

def main():
    p = argparse.ArgumentParser()
    for n in ('inputs', 'assets', 'assignment', 'source-seal', 'out'): p.add_argument('--'+n, type=Path, required=True)
    for n in ('source-sha', 'input-sha'): p.add_argument('--'+n, required=True)
    p.add_argument('--validate-only', action='store_true');a = p.parse_args()
    verify(Path.cwd(), str(a.source_seal), a.source_sha)
    from projects.g_agreement.e135 import inputs, runner
    loaded = inputs.load(a.inputs, a.input_sha);xs, deltas = loaded[0], loaded[1];assert deltas.shape == (168, 5120)
    from projects.g_agreement.e101.runner import dependencies  # every module run() needs, imported before any assignment or model
    from projects.g_agreement.e101 import runner109
    from mats.readers.olens import TRAINED_LAYERS
    assert callable(dependencies) and callable(runner.capture_answer_batch) and callable(runner109.backend87) and set(LAYERS) <= set(TRAINED_LAYERS)
    if a.validate_only: print('VALIDATE_OK', len(xs), sum(len(j) for j in runner.batches(xs, 8)), 2*len(xs));return
    ass = read(a.assignment)
    assert ass['experiment'] == 'E135' and ass['pod_id'] == os.environ.get('RUNPOD_POD_ID') and ass['gpu_type'] == 'H200' and ass['allocation_verified'] and ass['daily_budget_verified']
    assert ass['source_sha256'] == a.source_sha and ass['input_sha256'] == a.input_sha and ass['assets_sha256'] == sha(a.assets)
    assert ass['cap_seconds']==2880 and ass['absolute_deadline_epoch'] == min(ass['pod_created_epoch']+2880,1793364600) and ass['pod_created_epoch'] < 1793354400 and ass['cap_seconds']*5.29/3600 <= 25
    assert len(xs)==168 and set(float(x['alpha']) for x in xs)=={6.0}
    import torch  # inline single-H200 check (as I-2's e123_native233); e100.worker is not in C's E126 source archive
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1 and 'H200' in torch.cuda.get_device_name(0), 'one H200'
    a.out.mkdir(parents=True, exist_ok=False);write(a.out/'ASSIGNMENT.json', ass);write(a.out/'INVENTORY.json', dict(ids=[x['id'] for x in xs], source_sha256=a.source_sha, input_sha256=a.input_sha))
    c = Custody(ass, a.out);status = 'FAILED'
    timer = threading.Timer(max(0, ass['absolute_deadline_epoch']-time.time()-30), lambda: os.kill(os.getpid(), signal.SIGKILL));timer.daemon = True;timer.start()
    try: status = run(xs, deltas, a.assets, a.out, c)
    except BaseException as e: write(a.out/'FAILURE.json', dict(type=type(e).__name__, message=str(e)[:400]));raise
    finally:
        timer.cancel();files = [q for q in a.out.rglob('*') if q.is_file() and q.name != 'OUTPUT_SEAL.json'];real = [q for q in files if q.parent.name in ('jobs', 'capture', 'answers')]
        first = min(real, key=lambda q: q.stat().st_mtime_ns) if real else None
        write(a.out/'OUTPUT_SEAL.json', dict(experiment='E135', status=status, source_sha256=a.source_sha, input_sha256=a.input_sha, labels_cpu_only=True, judging=False, reader_calls=0, outputs_unopened=True,
              first_output_utc=datetime.fromtimestamp(first.stat().st_mtime, timezone.utc).isoformat() if first else 'unknown',
              first_output_evidence=dict(member=str(first.relative_to(a.out)), sha256=sha(first)) if first else None, files={str(q.relative_to(a.out)): sha(q) for q in files}))
if __name__ == '__main__': main()
