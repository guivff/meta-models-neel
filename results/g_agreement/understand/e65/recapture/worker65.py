"""E65 raw post-block44 forward-only recapture. No labels, readers or fitting."""
import argparse
import importlib.metadata
import math
import os
from pathlib import Path
import signal
import statistics
import time
import numpy as np
from common65 import *


class Captured(Exception):
    def __init__(self, vectors): self.vectors = vectors


class NoFit(TimeoutError): pass
class OperationalSetupError(OSError): pass


def blocks(model):
    for path in ('model.layers', 'model.language_model.layers'):
        cur = model
        try:
            for key in path.split('.'): cur = getattr(cur, key)
            if len(cur) == 64: return cur
        except AttributeError: pass
    raise ValueError('Pinned target must have64 decoder blocks')


def capture_batch(model, layer, items, device, dim=DIM):
    """Keep original full prompts; right padding never enters captured spans."""
    import torch
    width = max(len(x['ids']) for x in items)
    ids = torch.zeros((len(items), width), dtype=torch.long, device=device)
    mask = torch.zeros_like(ids)
    for i, x in enumerate(items):
        ids[i, :len(x['ids'])] = torch.tensor(x['ids'], device=device)
        mask[i, :len(x['ids'])] = 1
    calls = []
    def hook(_module, _inputs, output):
        h = output[0] if isinstance(output, tuple) else output
        require(h.shape == (len(items), width, dim), 'Block44 capture shape mismatch')
        vectors = [h[i, x['start']:x['stop']].detach().to(torch.float16).cpu().numpy().copy()
                   for i, x in enumerate(items)]
        require(all(np.isfinite(v).all() for v in vectors), 'Nonfinite fp16 capture')
        calls.append(True)
        # Upper blocks and the vocabulary head cannot change these raw vectors.
        raise Captured(vectors)
    handle = layer.register_forward_hook(hook)
    try:
        try:
            with torch.inference_mode():
                model(input_ids=ids, attention_mask=mask, use_cache=False, logits_to_keep=1)
        except Captured as result:
            require(len(calls) == 1, 'Capture must visit exactly block44 once')
            return result.vectors
        raise ValueError('Block44 capture hook did not fire')
    finally: handle.remove()


class Backend:
    def __init__(self):
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM
        expected = read(HERE / 'RUNTIME_PINS.json')
        names = ('torch', 'transformers', 'flash-linear-attention', 'fla-core', 'causal-conv1d', 'triton', 'tokenizers', 'numpy')
        self.runtime = {k: importlib.metadata.version(k) for k in names}
        if not all(self.runtime[k] == expected[k] for k in names):
            raise OperationalSetupError('Pinned forward runtime required')
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise OperationalSetupError('Exactly one CUDA GPU required')
        torch.set_num_threads(8); torch.manual_seed(20261027)
        torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        snapshot = snapshot_download(TARGET, revision=REVISION, local_files_only=True)
        require(sha(Path(snapshot) / 'tokenizer.json') == TOKENIZER_SHA, 'Pinned tokenizer required')
        self.model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.bfloat16,
            device_map='cuda', local_files_only=True)
        self.model.eval().requires_grad_(False)
        self.layer = blocks(self.model)[BLOCK]; self.device = next(self.model.parameters()).device
        self.runtime.update(model_repo=TARGET, revision=REVISION, adapter='none', block=BLOCK,
            indexing='zero-based decoder post-block output', storage_dtype='float16',
            device=torch.cuda.get_device_name(), early_stop_after_capture=True)

    def capture(self, items): return capture_batch(self.model, self.layer, items, self.device)


def memory_safe(total, free, reserved):
    return min(free, total - reserved) >= max(4 * 1024**3, .05 * total)


def probes(chunks):
    indices = [len(chunks) - 1, max(range(len(chunks)), key=lambda i: len(chunks[i]) * len(chunks[i][-1]['ids'])), len(chunks)//2]
    return [chunks[i] for i in dict.fromkeys(indices)]


def forecast(chunks, measurements):
    return sum(min(m['median_seconds'] * max(1., len(c)/m['sequences'])
                   * max(1., len(c[-1]['ids'])/m['max_tokens'])**2 for m in measurements) for c in chunks)


def benchmark(backend, items, check):
    import torch
    results = []
    for size in (32, 64):
        check(); torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
        chunks = batches(items, size); entry = {'batch_size': size, 'measurements': []}
        try:
            for chunk in probes(chunks):
                check(); backend.capture(chunk); torch.cuda.synchronize()
                times = []
                for _ in range(3):
                    check(); torch.cuda.synchronize(); t = time.monotonic(); backend.capture(chunk)
                    torch.cuda.synchronize(); times.append(time.monotonic() - t)
                median = statistics.median(times)
                entry['measurements'].append({'sequences': len(chunk), 'max_tokens': len(chunk[-1]['ids']),
                    'timings_seconds': times, 'median_seconds': median,
                    'prompt_tokens_per_second': sum(len(x['ids']) for x in chunk)/median})
            free, total = torch.cuda.mem_get_info(); reserved = torch.cuda.max_memory_reserved()
            entry.update(total_bytes=total, free_after_bytes=free, peak_reserved_bytes=reserved,
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                status='MEMORY_SAFE' if memory_safe(total, free, reserved) else 'INSUFFICIENT_HEADROOM')
            if entry['status'] == 'MEMORY_SAFE': entry['forecast_seconds'] = forecast(chunks, entry['measurements'])
        except torch.cuda.OutOfMemoryError: entry['status'] = 'CUDA_OOM_BEFORE_PRODUCTION'
        torch.cuda.empty_cache(); results.append(entry)
    valid = [x for x in results if x['status'] == 'MEMORY_SAFE']
    return results, min(valid, key=lambda x: x['forecast_seconds']) if valid else None


def assignment_check(a, request, now=None, pod_id=None):
    now = time.time() if now is None else now
    pod_id = os.environ.get('RUNPOD_POD_ID') if pod_id is None else pod_id
    require(a.get('issuer') == 'integrator' and a.get('experiment') == 'E65' and a.get('gpu_count') == 1
            and bool(pod_id) and a.get('pod_id') == pod_id, 'Exact own-pod assignment required')
    require(all(a.get(k) is True for k in ('source_pushed', 'external_hardstop_verified', 'hold_renewer_verified', 'separate_pod_verified')),
            'Published source and external own-pod custody required')
    require(a.get('request_sha256') == sha(HERE / 'LAUNCH_REQUEST.json')
            and a.get('source_seal_sha256') == request['source_seal_sha256'] == sha(HERE / 'POD_SOURCE_SEAL.json')
            and a.get('input_seal_sha256') == request['input_seal_sha256'] == sha(CACHE / 'pod_inputs/INPUT_SEAL.json'),
            'Exact request/source/input assignment pins required')
    commit = a.get('source_commit', '')
    require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'Exact published commit required')
    for k in ('provider_created_epoch', 'allocated_gpu_seconds', 'previous_gpu_seconds', 'deadline_epoch', 'setup_deadline_epoch'):
        require(type(a.get(k)) in (int, float) and math.isfinite(a[k]), 'Finite custody clocks required')
    created, allocation = a['provider_created_epoch'], a['allocated_gpu_seconds']
    require(a['previous_gpu_seconds'] == 0 and RESERVE < allocation <= CAP, 'Separate1080s stage cap exceeded')
    require(created <= now < a['setup_deadline_epoch'] <= min(created + SETUP_MAX, a['deadline_epoch'] - RESERVE)
            and a['setup_deadline_epoch'] < a['deadline_epoch'] <= min(created + allocation, STOP), 'Invalid setup/provider/programme clock')
    return a['deadline_epoch'] - RESERVE


def run(backend, bank, items, positions, out, deadline, check):
    ordered = sorted(items, key=lambda x: (len(x['ids']), x['id']))
    measurements, selected = benchmark(backend, ordered, check)
    dump(out / 'BENCHMARK.json', {'candidates': measurements, 'selected_batch_size': selected['batch_size'] if selected else None,
        'real_frozen_prompts': True, 'pilot_activations_saved': False})
    if selected is None: raise NoFit('Neither32 nor64 fits memory')
    remaining = selected['forecast_seconds']; now = time.time()
    fit = now + 1.5 * remaining + 360 < deadline
    dump(out / 'FORECAST.json', {'status': 'FIT' if fit else 'NO_FIT', 'admitted_epoch': now,
        'remaining_forecast_seconds': remaining, 'science_multiplier': 1.5, 'science_cushion_seconds': 360,
        'production_deadline_epoch': deadline, 'retrieval_reserve_seconds': RESERVE,
        'provider_cap_seconds': CAP, 'batch_size': selected['batch_size'], 'all_items': len(items),
        'all_positions': positions, 'scope_reduction_allowed': False})
    if not fit: raise NoFit('Full frozen recapture does not fit1080s provider cap')
    check(); dump(out / 'PRODUCTION.STARTED.json', {'started_epoch': time.time()})
    arr = np.lib.format.open_memmap(out / 'ACTIVATIONS.fp16.npy', mode='w+', dtype=np.float16, shape=(positions, DIM))
    seen = set()
    for chunk in batches(ordered, selected['batch_size']):
        check(); values = backend.capture(chunk)
        require(len(values) == len(chunk), 'Capture batch count mismatch')
        for item, vectors in zip(chunk, values):
            count = item['stop'] - item['start']; offset = item['offset']
            require(item['id'] not in seen and vectors.shape == (count, DIM)
                    and vectors.dtype == np.float16 and np.isfinite(vectors).all(), 'Capture identity/shape/dtype failure')
            arr[offset:offset+count] = vectors; seen.add(item['id'])
    require(seen == {x['id'] for x in items}, 'Missing/duplicate capture')
    arr.flush(); del arr; check()
    dump(out / 'OFFSETS.json', {'experiment': 'E65', 'schema': 'E65_CAPTURE_OFFSETS_V1', 'dtype': 'float16',
        'shape': [positions, DIM], 'block': BLOCK, 'indexing': 'zero-based post-block raw residual',
        'token_offsets': 'start inclusive, stop exclusive; read token=stop-1; offset indexes flat vector rows',
        'rows': [{'key': row['key'], 'items': [{'id': x['id'], 'prompt_tokens': len(x['ids']),
                  'start': x['start'], 'stop': x['stop'], 'offset': x['offset'], 'count': x['stop']-x['start']}
                  for x in row['items']]} for row in bank['rows']]})


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--assignment', type=Path); parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args(); source_verify(); bank, items, positions = load_inputs()
    if args.preflight:
        print(__import__('json').dumps({'status': 'PREFLIGHT_PASS', 'rows': len(bank['rows']), 'items': len(items),
            'positions': positions, 'output_bytes_data': positions * DIM * 2, 'maximum_prompt_tokens': max(len(x['ids']) for x in items),
            'source_seal_sha256': sha(HERE / 'POD_SOURCE_SEAL.json'), 'input_seal_sha256': sha(CACHE / 'pod_inputs/INPUT_SEAL.json'),
            'GPU_calls': 0})); return
    require(args.assignment is not None, 'Integrator assignment required')
    request = read(HERE / 'LAUNCH_REQUEST.json')
    require(request.get('status') == 'READY' and request['rows'] == len(bank['rows']) and request['items'] == len(items)
            and request['positions'] == positions, 'Exact READY scope required')
    assignment = read(args.assignment); deadline = assignment_check(assignment, request)
    dump(CACHE / 'WORKER.RUN_ONCE.json', {'started_epoch': time.time(), 'assignment_sha256': sha(args.assignment)})
    out = CACHE / 'out-20261027'; out.mkdir(exist_ok=False)
    def expired(*_): raise NoFit('E65 absolute custody deadline')
    def check():
        if time.time() >= deadline: expired()
    old = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(.001, min(deadline, assignment['setup_deadline_epoch'])-time.time()))
    status, category = 'INCOMPLETE', None
    try:
        backend = Backend()
        if time.time() >= assignment['setup_deadline_epoch']: raise NoFit('Setup clock exhausted')
        signal.setitimer(signal.ITIMER_REAL, max(.001, deadline-time.time())); dump(out / 'RUNTIME.json', backend.runtime)
        run(backend, bank, items, positions, out, deadline, check); check(); status = 'COMPLETE'
    except Exception as exc:
        category = ('OPERATIONAL_NO_FIT' if isinstance(exc, NoFit) else 'OPERATIONAL_FAILURE'
                    if isinstance(exc, (OSError, ImportError, MemoryError)) or type(exc).__name__ == 'OutOfMemoryError'
                    else 'PARITY_OR_VALIDITY_NO_RETRY')
        dump(out / 'FAILURE.json', {'error_type': type(exc).__name__, 'category': category, 'guard_preserved': True, 'scope_reduced': False})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old)
        dump(out / 'CUSTODY.json', {'assignment': assignment, 'assignment_sha256': sha(args.assignment),
            'completed_epoch': time.time(), 'request_sha256': sha(HERE / 'LAUNCH_REQUEST.json'),
            'source_seal_sha256': sha(HERE / 'POD_SOURCE_SEAL.json'), 'input_seal_sha256': sha(CACHE / 'pod_inputs/INPUT_SEAL.json')})
        dump(out / 'OUTPUT_SEAL.json', {'experiment': 'E65', 'status': status, 'failure_category': category,
            'files': {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}})


if __name__ == '__main__': main()
