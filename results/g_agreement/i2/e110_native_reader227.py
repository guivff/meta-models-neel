"""Frozen E110 selected-bank capture and native readouts; no labels or selection.

Both original readers, full selected grid, H200 only, registered 5400s ceiling.
Runtime/dependencies are the original E114/E85 source archive, hash-bound outside.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import threading
import time
import numpy as np


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(p, value, replace=False):
    p = Path(p)
    if not replace:
        with p.open('x') as f:
            json.dump(value, f, indent=2)
            f.write('\n')
    else:
        q = p.with_suffix('.new')
        q.write_text(json.dumps(value, indent=2) + '\n')
        q.replace(p)


def validate(items):
    require(60 <= len(items) <= 3000, 'complete selected bank60..3000; no sampling')
    require(len(items) == len({x['id'] for x in items}), 'unique frozen IDs')
    for x in items:
        require(set(x) == {'id', 'prompt', 'input_ids', 'read_position'}, 'public fields only')
        require(isinstance(x['prompt'], str) and x['input_ids'], 'original prompt/tokens')
        require(all(type(t) is int and t >= 0 for t in x['input_ids']), 'original token IDs')
        require(x['read_position'] == len(x['input_ids']) - 1, 'native twohop final read token')
    return [dict(id=x['id'], text=x['prompt'], ids=x['input_ids'], read_index=x['read_position']) for x in items]


def fit(elapsed, phases, cap):
    require(elapsed >= 0 and 0 < cap <= 5400, 'registered reader custody ceiling')
    require(all(n >= 0 and seconds > 0 for n, seconds in phases), 'source-bound timings')
    need = elapsed + 1.25 * sum(n * seconds for n, seconds in phases) + 60
    return dict(status='ADMIT' if need <= cap else 'NO_FIT', need_seconds=need,
                elapsed_seconds=elapsed, margin=1.25, original_cap_seconds=cap)


def backend(assets):
    from runtime import Runtime
    from contract import ROOT
    class Native(Runtime):
        def capture_joint(self, items):
            import sys
            import torch
            sys.path.insert(0, str(ROOT / 'external/mats-nla-workspace/src'))
            from mats.capture import capture
            self.check_tokens(items)
            model, tok, cm = self.subject()
            with cm, torch.inference_mode():
                v = capture(model, [x['ids'] for x in items], (44, 42),
                            [[x['read_index']] for x in items], batch_size=8,
                            pad_id=tok.pad_token_id or 0)
            return {layer: v[layer][:, 0].float().cpu().numpy() for layer in (44, 42)}
    return Native(assets)


def run(a, b):
    ass = read(a.assignment)
    start, end, cap = ass['pod_created_epoch'], ass['absolute_deadline_epoch'], ass['cap_seconds']
    require(ass['experiment'] == 'E110_READERS' and ass['gpu_type'] == 'H200', 'approved H200 reader stage only')
    require(end == start + cap and 0 < cap <= 5400 and time.time() < start + 900, 'original clocks/setup900')
    require(sha(a.inputs) == a.input_sha256 and sha(a.timings) == a.timings_sha256, 'frozen input/timing bytes')
    require(ass['selection_seal_sha256'] == a.selection_sha256 and ass['inventory_seal_sha256'] == a.inventory_sha256,
            'CPU selection and pre-output committed inventory binding')
    items = validate(read(a.inputs))
    require(ass['selected_count'] == len(items), 'all selected survivors and matched rights')
    retained = read(a.timings)
    rates = {r: max(x['seconds'] for x in retained if x['phase'] == r + '_native') for r in ('oracle', 'nla')}
    nla_setup = sum(max(x['seconds'] for x in retained if x['phase'] == n)
                    for n in ('nla_setup', 'nla_warmup_discarded'))
    a.out.mkdir(exist_ok=False)
    for n in ['capture', 'oracle', 'nla']:
        (a.out / n).mkdir()
    events, captures, capture_profile = [], {44: {}, 42: {}}, []
    def timed(name, fn):
        require(time.time() < end - 60, 'original absolute deadline')
        before = time.monotonic()
        result = fn()
        b.sync()
        events.append(dict(phase=name, seconds=time.monotonic() - before))
        write(a.out / 'TIMINGS.json', events, replace=True)
        return result
    def admit(label, phases):
        d = fit(time.time() - start, phases, cap)
        write(a.out / (label + '_ADMISSION.json'), d)
        return d['status'] == 'ADMIT'
    b.native_batch_size = 32
    timed('oracle_setup', b.load_oracle)
    b.seed(20261029)
    require(time.time() < start + 900, 'original setup900')
    chunks = [items[i:i + 64] for i in range(0, len(items), 64)]
    batches = math.ceil(len(items) / 32)
    status = 'COMPLETE'
    for i, xs in enumerate(chunks):
        v = timed('capture44_42', lambda xs=xs: b.capture_joint(xs))
        for layer in (44, 42):
            require(v[layer].shape == (len(xs), 5120) and np.isfinite(v[layer]).all(), 'finite original read-site capture')
            captures[layer].update({x['id']: h.copy() for x, h in zip(xs, v[layer])})
        np.savez(a.out / 'capture' / ('%04d.npz' % i), ids=np.array([x['id'] for x in xs]),
                 acts44=v[44], acts42=v[42])
        capture_profile.append(events[-1]['seconds'])
        if i + 1 == min(3, len(chunks)):
            if not admit('CAPTURE_PROFILE', [(len(chunks) - i - 1, max(capture_profile)),
                    (batches, rates['oracle']), (1, nla_setup), (batches, rates['nla'])]):
                status = 'NO_FIT'
                break
    if status == 'COMPLETE':
        require(all(len(captures[l]) == len(items) for l in (44, 42)), 'complete selected capture grid')
        for reader, layer in [('oracle', 44), ('nla', 42)]:
            if reader == 'nla':
                if not admit('NLA_PRELOAD', [(1, nla_setup), (batches, rates['nla'])]):
                    status = 'NO_FIT'
                    break
                timed('nla_setup', b.load_nla)
                timed('nla_warmup_discarded', lambda: b.native('nla', np.zeros((32, 5120), np.float32), False))
                b.seed(20261029)
            profile = []
            for i, k in enumerate(range(0, len(items), 32)):
                xs = items[k:k + 32]
                acts = np.array([captures[layer][x['id']] for x in xs], dtype=np.float32)
                before = acts.tobytes()
                output = timed(reader + '_native', lambda: b.native(reader, acts, False))
                require(acts.tobytes() == before and len(output) == len(xs) and all(len(g) == 1 for g in output),
                        'unaltered activations / one greedy original native per selected item')
                write(a.out / reader / ('%06d.json' % i),
                      [dict(id=x['id'], reader=reader, output=g[0]) for x, g in zip(xs, output)])
                profile.append(events[-1]['seconds'])
                if i + 1 == min(3, batches):
                    phases = [(batches - i - 1, max(profile))]
                    if reader == 'oracle':
                        phases += [(1, nla_setup), (batches, rates['nla'])]
                    if not admit(reader.upper() + '_PROFILE', phases):
                        status = 'NO_FIT'
                        break
            if status != 'COMPLETE':
                break
    counts = {r: sum(len(read(p)) for p in (a.out / r).glob('*.json')) for r in ('oracle', 'nla')}
    if status == 'COMPLETE':
        require(all(n == len(items) for n in counts.values()), 'full both-reader grid, no denominator shrink')
    files = sorted(p for p in a.out.rglob('*') if p.is_file())
    first = min([p for p in files if p.suffix == '.npz' or p.parent.name in ('oracle', 'nla')], key=lambda p: p.stat().st_mtime_ns)
    write(a.out / 'OUTPUT_SEAL.json', dict(experiment='E110_READERS', status=status,
          source_sha256=a.source_sha256, input_sha256=a.input_sha256,
          selection_seal_sha256=a.selection_sha256, inventory_seal_sha256=a.inventory_sha256,
          model_revision='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9', GPU_type='H200',
          reader_blocks=dict(oracle=44, nla=42), greedy_max_new_tokens=128, temperature=0,
          native_batch_size=32, capture_batch_size=8, one_greedy_readout_per_item=True,
          all_selected_items_retained=True, labels_cpu_only=True, native_counts=counts,
          capture_count=len(captures[44]), synthetic=getattr(a, 'synthetic', False),
          partials_excluded_if_not_complete=True,
          first_output_evidence=dict(member=str(first.relative_to(a.out)), mtime_ns=first.stat().st_mtime_ns,
                                     sha256=sha(first)), files={str(p.relative_to(a.out)): sha(p) for p in files}))
    return status


def main():
    p = argparse.ArgumentParser()
    for k in ['inputs', 'assets', 'assignment', 'timings', 'out']:
        p.add_argument('--' + k, type=Path, required=True)
    for k in ['input-sha256', 'timings-sha256', 'selection-sha256', 'inventory-sha256', 'source-sha256']:
        p.add_argument('--' + k, required=True)
    a = p.parse_args()
    end = read(a.assignment)['absolute_deadline_epoch']
    timer = threading.Timer(max(0, end - time.time() - 10), lambda: os.kill(os.getpid(), signal.SIGKILL))
    timer.daemon = True
    timer.start()
    try:
        run(a, backend(a.assets))
    finally:
        timer.cancel()


if __name__ == '__main__':
    main()
