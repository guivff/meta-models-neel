"""E58b: raw base-Qwen prompt-position projection and continuation likelihoods."""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import signal
import shutil
import statistics
import time
import numpy as np
from batching58 import prefix_plan, batches, probe_batches, estimate_batches, accumulate, finish, choose_budget
from common58 import *
from projection58 import PCAMoments, check_basis, projection_hook, random_basis


class NoFit(TimeoutError):
    pass


class OperationalSetupError(OSError):
    pass


def validate_bank(bank):
    require(set(bank) == {'experiment', 'schema', 'pca_population', 'rows'}
            and bank['experiment'] == 'E58b' and bank['schema'] == 'E58B_POD_BLIND_V2',
            'Exact blind pod schema required')
    rows = bank['rows']
    require(rows and len({r['key'] for r in rows}) == len(rows), 'Unique nonempty opaque row catalog required')
    require(bank['pca_population'] == pca_population(rows), 'Exact pooled-PCA fallback rule required')
    all_ids = []
    for row in rows:
        require(set(row) == {'key', 'dev', 'test'}, 'Unexpected pod row metadata')
        require(isinstance(row['key'], str) and len(row['key']) == 32
                and all(c in '0123456789abcdef' for c in row['key']), 'Opaque pod row ID required')
        for split in ('dev', 'test'):
            items = row[split]
            require(len(items) == 84, 'Full frozen 84-item split required')
            for item in items:
                expected = {'id', 'split', 'ids', 'pairs'} if split == 'test' else {'id', 'split', 'ids'}
                require(set(item) == expected, 'Unexpected pod item metadata')
                require(isinstance(item['id'], str) and len(item['id']) == 32
                        and all(c in '0123456789abcdef' for c in item['id']), 'Opaque pod item ID required')
                require(item['split'] == split and item['ids']
                        and all(type(t) is int and t >= 0 for t in item['ids']), 'Exact frozen prompt tokens required')
                all_ids.append(item['id'])
                if split == 'test':
                    require(item['pairs'], 'Every frozen candidate pair required')
                    for pair in item['pairs']:
                        require(set(pair) == {'A_ids', 'B_ids'} and pair['A_ids'] and pair['B_ids']
                                and pair['A_ids'] != pair['B_ids'], 'Exact blind candidate-token schema required')
                        require(all(type(t) is int and t >= 0 for t in pair['A_ids'] + pair['B_ids']),
                                'Valid candidate token IDs required')
    require(len(all_ids) == len(set(all_ids)), 'Duplicate pod item IDs')
    return rows


def validate_pod_directory(folder):
    folder = Path(folder)
    files = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    require(files == {'BANK.json', 'J384.npy', 'INPUT_SEAL.json'}
            and not any(p.is_symlink() for p in folder.rglob('*')), 'Pod input file whitelist violation')
    record = read(folder / 'INPUT_SEAL.json')
    require(set(record) == {'experiment', 'schema', 'files'}
            and record['experiment'] == 'E58b' and record['schema'] == 'E58B_POD_INPUT_SEAL_V2'
            and set(record['files']) == {'BANK.json', 'J384.npy'}, 'Pod seal file whitelist violation')
    verify(folder, 'INPUT_SEAL.json')
    return validate_bank(read(folder / 'BANK.json'))


def pca_population(rows):
    return 'pooled_dev_read_points' if sum(len(r['dev']) for r in rows) >= 768 else 'pooled_dev_prompt_positions'


def assignment_check(a, request_sha, input_sha, now=None, pod_id=None):
    now = time.time() if now is None else now
    pod_id = os.environ.get('RUNPOD_POD_ID') if pod_id is None else pod_id
    require(a.get('issuer') == 'integrator' and a.get('experiment') == 'E58b'
            and a.get('gpu_count') == 1 and a.get('pod_id') == pod_id and bool(pod_id), 'Exact pod assignment required')
    require(a.get('request_sha256') == request_sha and a.get('input_seal_sha256') == input_sha
            and a.get('source_seal_sha256') == sha(HERE / 'POD_SOURCE_SEAL.20261027.json'), 'Assignment bindings required')
    require(all(a.get(k) is True for k in ('source_pushed', 'external_hardstop_verified', 'hold_renewer_verified')),
            'Pushed source and external custody guards required')
    commit = a.get('source_commit', '')
    require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'Exact source commit required')
    for key in ('provider_created_epoch', 'allocated_gpu_seconds', 'previous_gpu_seconds', 'deadline_epoch', 'setup_deadline_epoch'):
        require(finite_number(a.get(key)), 'Finite custody timing fields required')
    created, allocation, previous = (a[k] for k in ('provider_created_epoch', 'allocated_gpu_seconds', 'previous_gpu_seconds'))
    require(previous >= 0 and RESERVE < allocation and previous + allocation <= MAX_CAP, 'E58b authorized total cap exceeded')
    require(created <= now < a['setup_deadline_epoch'] <= min(created + 1500, a['deadline_epoch'] - RESERVE), 'Invalid/expired setup clock')
    require(a['setup_deadline_epoch'] < a['deadline_epoch'] <= min(created + allocation, PROGRAMME_STOP), 'Invalid absolute/programme clock')
    require(a.get('conditional_extension_authorized') is True and a.get('prior_no_production_verified') is True
            and type(a.get('retry_number')) is int and a['retry_number'] == 1
            and a.get('budget_watch_verified') is True, 'Authorized rebuild, prior custody and selected-budget watcher required')
    return a['deadline_epoch'] - RESERVE


def blocks(model):
    for path in ('model.layers', 'model.language_model.layers'):
        current = model
        try:
            for part in path.split('.'):
                current = getattr(current, part)
            if len(current) == 64:
                return current
        except AttributeError:
            pass
    raise ValueError('Pinned target must have 64 decoder blocks')


class Backend:
    def __init__(self):
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM
        expected = read(ROOT / 'results/g_agreement/blindspot/s79/RUNTIME_PINS.json')
        names = ('torch', 'transformers', 'flash-linear-attention', 'fla-core', 'causal-conv1d', 'triton', 'tokenizers', 'numpy')
        self.runtime = {name: importlib.metadata.version(name) for name in names}
        if not all(self.runtime[k] == expected[k] for k in names):
            raise OperationalSetupError('Pinned forward runtime required')
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise OperationalSetupError('One CUDA GPU required')
        torch.set_num_threads(8)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        torch.manual_seed(20261027)
        snapshot = snapshot_download(TARGET, revision=REVISION, local_files_only=True)
        require(sha(Path(snapshot) / 'tokenizer.json') == '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42',
                'Pinned tokenizer required')
        self.model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.bfloat16,
            device_map='cuda', local_files_only=True)
        self.model.eval().requires_grad_(False)
        self.layer = blocks(self.model)[BLOCK]
        self.device = next(self.model.parameters()).device
        self.runtime.update(model_repo=TARGET, model_revision=REVISION, adapter='none',
            block=BLOCK, block_indexing='zero-based post-block output', cuda_device=torch.cuda.get_device_name())

    def capture(self, items, population, moments):
        import torch
        require(all(x['split'] == 'dev' for x in items), 'PCA may only capture dev prompts')
        lengths = [len(x['ids']) for x in items]
        ids = torch.zeros((len(items), max(lengths)), dtype=torch.long, device=self.device)
        mask = torch.zeros_like(ids)
        for i, x in enumerate(items):
            ids[i, :lengths[i]] = torch.tensor(x['ids'], device=self.device)
            mask[i, :lengths[i]] = 1
        calls = []
        def capture_hook(_module, _inputs, output):
            h = output[0] if isinstance(output, tuple) else output
            selected = h[mask.bool()] if population == 'pooled_dev_prompt_positions' else h[
                torch.arange(len(items), device=self.device), torch.tensor(lengths, device=self.device) - 1]
            moments.add(selected)
            calls.append(True)
        handle = self.layer.register_forward_hook(capture_hook)
        try:
            with torch.inference_mode():
                self.model(input_ids=ids, attention_mask=mask, logits_to_keep=1, use_cache=False)
        finally:
            handle.remove()
        require(len(calls) == 1, 'Capture must visit exactly block 44 once')

    def score_nodes(self, nodes, q=None):
        """One left-padded conditional-prefix batch; final-position logits only."""
        import torch
        width = max(len(n['ids']) for n in nodes)
        ids = torch.zeros((len(nodes), width), dtype=torch.long, device=self.device)
        mask = torch.zeros_like(ids)
        starts = []
        for i, node in enumerate(nodes):
            start = width - len(node['ids']); starts.append(start)
            ids[i, start:] = torch.tensor(node['ids'], device=self.device)
            mask[i, start:] = 1
        positions = (mask.cumsum(-1) - 1).masked_fill(mask == 0, 0)
        handle = self.layer.register_forward_hook(projection_hook(q, [n['prompt_length'] for n in nodes], starts)) if q is not None else None
        try:
            with torch.inference_mode():
                output = self.model(input_ids=ids, attention_mask=mask, position_ids=positions,
                                    logits_to_keep=1, use_cache=False)
                probabilities = output.logits[:, -1, :].float().log_softmax(-1)
                rr, tt = [], []
                for i, node in enumerate(nodes):
                    for token in node['targets']: rr.append(i); tt.append(token)
                values = probabilities[torch.tensor(rr, device=self.device), torch.tensor(tt, device=self.device)].cpu().tolist()
        finally:
            if handle is not None: handle.remove()
        result = [{} for n in nodes]
        for i, token, value in zip(rr, tt, values): result[i][token] = value
        return result

    def score(self, jobs, q=None):
        # Compatibility wrapper used only for small numerical verification.
        rows = [{'key': 'verification', 'test': []}]
        selected = {}
        for item, j in jobs: selected.setdefault(item['id'] if 'id' in item else str(id(item)), item)
        for opaque, item in selected.items(): rows[0]['test'].append({**item, 'id': opaque})
        nodes, candidates = prefix_plan(rows)
        terms = {key: [None] * n for key, n in candidates.items()}
        accumulate(terms, nodes, self.score_nodes(nodes, q)); values = finish(terms)
        return [(values['verification', item['id'] if 'id' in item else str(id(item)), j, 'A'],
                 values['verification', item['id'] if 'id' in item else str(id(item)), j, 'B']) for item, j in jobs]


def memory_safe(total, free, peak_reserved):
    margin = max(4 * 1024 ** 3, .05 * total)
    return min(free, total - peak_reserved) >= margin


def benchmark(backend, dev, nodes, q, check, population):
    import torch
    results = []
    for size in (32, 64):
        check(); torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
        entry = {'batch_size': size, 'capture': [], 'score': [], 'status': 'PENDING'}
        scratch = None
        try:
            scratch = PCAMoments(device=backend.device)
            for phase, probes in [('capture', probe_batches(dev, size)), ('score', probe_batches(nodes, size))]:
                for chunk in probes:
                    def call():
                        if phase == 'capture': backend.capture(chunk, population, scratch)
                        else: backend.score_nodes(chunk, q)
                    check(); call(); torch.cuda.synchronize()  # warmed, discarded
                    timings = []
                    for _ in range(3):
                        check(); torch.cuda.synchronize(); t = time.monotonic(); call()
                        torch.cuda.synchronize(); timings.append(time.monotonic() - t)
                    median = statistics.median(timings)
                    entry[phase].append({'sequences': len(chunk), 'max_tokens': max(len(x['ids']) for x in chunk),
                        'timings_seconds': timings, 'median_seconds': median,
                        'prefixes_per_second': len(chunk) / median,
                        'unpadded_tokens_per_second': sum(len(x['ids']) for x in chunk) / median})
            free, total = torch.cuda.mem_get_info()
            peak = torch.cuda.max_memory_reserved()
            entry.update(status='MEMORY_SAFE' if memory_safe(total, free, peak) else 'INSUFFICIENT_HEADROOM',
                total_bytes=total, free_after_bytes=free, peak_reserved_bytes=peak,
                peak_allocated_bytes=torch.cuda.max_memory_allocated())
            if entry['status'] == 'MEMORY_SAFE':
                entry['capture_forecast_seconds'] = estimate_batches(batches(dev, size), entry['capture'])
                entry['score_forecast_seconds'] = len(ARMS) * estimate_batches(batches(nodes, size), entry['score'])
                entry['full_remaining_estimate_seconds'] = entry['capture_forecast_seconds'] + entry['score_forecast_seconds']
        except torch.cuda.OutOfMemoryError:
            entry['status'] = 'CUDA_OOM_BEFORE_PRODUCTION'
        finally:
            del scratch
            torch.cuda.empty_cache()
        results.append(entry)
    valid = [r for r in results if r['status'] == 'MEMORY_SAFE']
    return results, min(valid, key=lambda r: r['full_remaining_estimate_seconds']) if valid else None


def run(backend, bank, qj, out, assignment, check, tighten):
    import torch
    started = time.monotonic()
    rows = validate_bank(bank)
    nodes, candidates = prefix_plan(rows)
    dev = sorted([x for r in rows for x in r['dev']], key=lambda x: (len(x['ids']), x['id']))
    bases = {'J': torch.as_tensor(qj, device=backend.device)}
    for i, seed in enumerate(SEEDS):
        check(); q = random_basis(seed); np.save(out / f'random_basis_seed{seed}.npy', q, allow_pickle=False)
        bases['random' + str(i)] = torch.as_tensor(q, device=backend.device)
    measurements, selected = benchmark(backend, dev, nodes, bases['J'], check, bank['pca_population'])
    dump(out / 'BENCHMARK.json', {'batch_candidates': measurements,
        'selected_batch_size': selected['batch_size'] if selected else None,
        'real_frozen_prefixes': True, 'pilot_scores_saved': False, 'scratch_moments_used_for_PCA': False})
    if selected is None: raise NoFit('Neither 32 nor 64 fits memory; no production')
    size = selected['batch_size']; chunks = batches(nodes, size)
    sample = probe_batches(nodes, size)[0]
    check(); a = backend.score_nodes(sample); check(); b = backend.score_nodes(sample, torch.zeros_like(bases['J']))
    require(a == b, 'No-edit/zero-projection parity failure; no retry')
    moments = PCAMoments(device=backend.device); capture_times = []
    for chunk in batches(dev, size):
        check(); torch.cuda.synchronize(); t = time.monotonic()
        backend.capture(chunk, bank['pca_population'], moments)
        torch.cuda.synchronize(); capture_times.append(time.monotonic() - t)
    check(); t = time.monotonic(); qpca, eigenvalues = moments.basis(); torch.cuda.synchronize()
    pca_seconds = time.monotonic() - t
    error = check_basis(qpca.cpu().numpy()); np.save(out / 'PCA_shared.npy', qpca.cpu().numpy(), allow_pickle=False)
    dump(out / 'PCA_shared.json', {'rows': [r['key'] for r in rows], 'dev_samples': moments.n,
        'dev_items': len(dev), 'population': bank['pca_population'], 'centered': True,
        'fallback_read_point_threshold': 768, 'test_activations_used': False,
        'same_subspace_for_every_row': True, 'projection_subtracts_PCA_mean': False,
        'rank': RANK, 'eigenvalues': eigenvalues, 'orthonormality_error': error})
    del moments; torch.cuda.empty_cache()
    remaining = selected['score_forecast_seconds']
    budget = choose_budget(assignment, remaining, time.time()); dump(out / 'BUDGET.json', budget)
    dump(out / 'FORECAST.json', {**budget, 'batch_size': size, 'score_forward_batches': len(chunks) * len(ARMS),
        'forecast_seconds': time.monotonic() - started + remaining,
        'conditional_prefixes_per_arm': len(nodes), 'capture_seconds': capture_times, 'shared_PCA_seconds': pca_seconds,
        'zero_projection_parity_exact': True, 'pilot_scores_used': False, 'frozen_rows': len(rows),
        'all_candidate_tokens_scored': True, 'scope_reduction_allowed': False})
    if budget['status'] != 'FIT': raise NoFit('Full frozen scope does not fit even the authorized extension')
    tighten(budget['production_deadline_epoch'])
    dump(out / 'PRODUCTION.STARTED.json', {'started_epoch': time.time(), 'batch_size': size})
    for arm in ARMS:
        terms = {key: [None] * n for key, n in candidates.items()}
        q = None if arm == 'none' else qpca if arm == 'PCA' else bases[arm]
        for chunk in chunks:
            check(); accumulate(terms, chunk, backend.score_nodes(chunk, q))
        values = finish(terms)
        with (out / 'scores.partial.jsonl').open('a') as f:
            for row in rows:
                for item in row['test']:
                    for j in range(len(item['pairs'])):
                        record = {'row': row['key'], 'id': item['id'], 'pair_index': j, 'arm': arm,
                            'seed': SEEDS[int(arm[-1])] if arm.startswith('random') else None,
                            'logp_A': values[row['key'], item['id'], j, 'A'], 'logp_B': values[row['key'], item['id'], j, 'B']}
                        f.write(json.dumps(record, allow_nan=False) + '\n')
            f.flush()
    shutil.copyfile(out / 'scores.partial.jsonl', out / 'scores.jsonl')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assignment', type=Path, required=True)
    a = parser.parse_args()
    source_verify('POD_SOURCE_SEAL.20261027.json')
    request = read(HERE / 'LAUNCH_REQUEST.json')
    require(request['source_seal_sha256'] == sha(HERE / 'POD_SOURCE_SEAL.20261027.json'), 'Request source-seal pin mismatch')
    require(request['status'] == 'READY' and request['input_seal_sha256'], 'Request is held; do not launch')
    inp = CACHE / 'pod_inputs_v2'
    require(sha(inp / 'INPUT_SEAL.json') == request['input_seal_sha256'], 'Exact staged input seal required')
    validate_pod_directory(inp)
    bank = read(inp / 'BANK.json')
    require(len(bank['rows']) == request['frozen_rows'], 'Request row scope mismatch')
    require(sha(inp / 'J384.npy') == J_SHA, 'Exact W-lens J384 export required')
    qj = np.load(inp / 'J384.npy', allow_pickle=False); check_basis(qj)
    assignment = read(a.assignment)
    deadline = assignment_check(assignment, sha(HERE / 'LAUNCH_REQUEST.json'), sha(inp / 'INPUT_SEAL.json'))
    CACHE.mkdir(parents=True, exist_ok=True)
    dump(CACHE / 'WORKER.rerun1.RUN_ONCE.json', {'assignment_sha256': sha(a.assignment), 'started_epoch': time.time()})
    out = CACHE / 'out-rerun1-batched-20261027'; out.mkdir(exist_ok=False)
    active_deadline = {'epoch': deadline}
    def expired(*_):
        raise NoFit('E58b absolute custody deadline')
    def check():
        if time.time() >= active_deadline['epoch']:
            expired()
    old = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(.001, min(deadline, assignment['setup_deadline_epoch']) - time.time()))
    status, category = 'INCOMPLETE', None
    try:
        backend = Backend()
        if time.time() >= assignment['setup_deadline_epoch']:
            raise NoFit('Setup clock exhausted')
        signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - time.time()))
        dump(out / 'RUNTIME.json', backend.runtime)
        def tighten(epoch):
            active_deadline['epoch'] = min(deadline, epoch)
            signal.setitimer(signal.ITIMER_REAL, max(.001, active_deadline['epoch'] - time.time()))
        run(backend, bank, qj, out, assignment, check, tighten)
        check(); status = 'COMPLETE'
    except Exception as exc:
        category = ('OPERATIONAL_NO_FIT' if isinstance(exc, NoFit) else 'OPERATIONAL_FAILURE'
                    if isinstance(exc, (OSError, ImportError, MemoryError)) or type(exc).__name__ == 'OutOfMemoryError'
                    else 'PARITY_OR_VALIDITY_NO_RETRY')
        dump(out / 'FAILURE.json', {'error_type': type(exc).__name__, 'category': category,
                                   'guard_preserved': True, 'scope_reduced': False})
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old)
        dump(out / 'CUSTODY.json', {'assignment_sha256': sha(a.assignment), 'assignment': assignment,
            'completed_epoch': time.time(), 'request_sha256': sha(HERE / 'LAUNCH_REQUEST.json'),
            'input_seal_sha256': request['input_seal_sha256'],
            'source_seal_sha256': sha(HERE / 'POD_SOURCE_SEAL.20261027.json')})
        seal(out, 'OUTPUT_SEAL.json', experiment='E58b', status=status, failure_category=category)


if __name__ == '__main__':
    main()
