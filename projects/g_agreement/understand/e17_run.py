"""§110 E17: integrator-only capture and four-channel acquisition.

The bank is committed before any model call. This worker sees no labels. It
captures block 44 on the prefix only, reconstructs the *real* following 16 tokens
with E1b's unchanged AR adapter, and scores the frozen Oracle continuation and
asked pairs. Both probes are fitted later, on dev only, after the output seal.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import gc
import json
import math
import os
from pathlib import Path
import signal
import statistics
import time

import numpy as np

from projects.g_agreement.blindspot import protocol as P, run as W
from .e15 import native_score
from .e15_pairs import PAIRS

CAP = 3600
SETUP = 2400
RETRIEVAL_RESERVE = 180
CAPTURE_BATCH = 8
SCORE_BATCH = 32
AR_BATCH = 8
FEATURES = ('prose_paren', 'python_string', 'list_depth')
CHANNELS = ('continuation', 'asked')
ARMS = ('true', 'random_donor', 'opposite_swap')


def source_hashes():
    names = set(P.code_hashes())
    names.update('projects/g_agreement/understand/' + n for n in
                 ('__init__.py', 'core.py', 'e6.py', 'e15.py', 'e15_pairs.py', 'e17_items.py', 'e17_run.py', 'e17_analysis.py'))
    names.update(('projects/g_agreement/w_claims/__init__.py',
                  'projects/g_agreement/w_claims/ar.py',
                  'projects/g_agreement/blindspot/ar_tests.py',
                  'results/g_agreement/understand/e17/REGISTERED_SECTION.md'))
    return {n: P.sha(P.ROOT / n) for n in sorted(names)}


def inputs(bank):
    """Validate the committed, label-free grid without importing a model."""
    bank = Path(bank)
    seal = P.verify(bank, 'INPUT_SEAL.json')
    W._labels_absent(bank)
    required = {'items.input.jsonl', 'manifest.json', 'phrasings.json', 'pairs.json'}
    if (set(seal['files']) != required
            or {str(p.relative_to(bank)) for p in bank.rglob('*') if p.is_file()} != required | {'INPUT_SEAL.json'}):
        raise ValueError('E17 staged bank must contain exactly the sealed allowlist')
    items = P.rows(bank / 'items.input.jsonl')
    if len(items) != 1920 or len({x['id'] for x in items}) != 1920:
        raise ValueError('E17 requires exactly 1920 unique items')
    allowed = {'id', 'pair_id', 'lexical_id', 'feature', 'cell', 'split', 'cluster', 'ids',
               'read_index', 'next16_ids', 'next16_text', 'random_donor_id', 'opposite_donor_id'}
    index = {x['id']: x for x in items}
    groups = defaultdict(list)
    for x in items:
        if set(x) != allowed or x['feature'] not in FEATURES or x['split'] not in ('dev', 'test'):
            raise ValueError('invalid label-free E17 schema')
        if (not x['ids'] or x['read_index'] != len(x['ids']) - 1 or len(x['next16_ids']) != 16
                or not isinstance(x['next16_text'], str) or not x['next16_text']
                or any(type(t) is not int or t < 0 for t in x['ids'] + x['next16_ids'])):
            raise ValueError('invalid capture index or next16 token slice')
        groups[x['feature'], x['cell'], x['split']].append(x)
        for key in ('random_donor_id', 'opposite_donor_id'):
            donor = index.get(x[key])
            if donor is None or any(donor[k] != x[k] for k in ('feature', 'cell', 'split')):
                raise ValueError('donor crosses feature, cell or split')
        random = index[x['random_donor_id']]
        if random['cluster'] != x['cluster'] or len(random['ids']) // 16 != len(x['ids']) // 16:
            raise ValueError('random donor crosses template family or length bin')
        opposite = index[x['opposite_donor_id']]
        if (opposite['id'] == x['id'] or opposite['opposite_donor_id'] != x['id']
                or opposite['pair_id'] != x['pair_id'] or opposite['read_index'] != x['read_index']):
            raise ValueError('opposite donor must be the aligned reciprocal twin')
    if any(len({x['cell'] for x in items if x['feature'] == f}) != n
           for f, n in zip(FEATURES, (4, 4, 2))):
        raise ValueError('four span cells and two list cells required')
    if len(groups) != 20 or any(len(g) != (64 if k[2] == 'dev' else 128) for k, g in groups.items()):
        raise ValueError('ten complete 32-dev/64-test pair cells required')
    for feature in FEATURES:
        dev = {x['cluster'] for x in items if x['feature'] == feature and x['split'] == 'dev'}
        test = {x['cluster'] for x in items if x['feature'] == feature and x['split'] == 'test'}
        if not dev or not test or dev & test:
            raise ValueError('template families leak across dev/test')
    phrasings = json.loads((bank / 'phrasings.json').read_text())
    if set(phrasings) != set(FEATURES):
        raise ValueError('three frozen W1 asked rows required')
    asked = {f: W._pairs(phrasings[f], 'olens') for f in FEATURES}
    from projects.g_agreement.blindspot.items import FEATURES as W1_FEATURES
    if any([tuple(p) for p in asked[f]] != W1_FEATURES[f].pairs('olens') for f in FEATURES):
        raise ValueError('asked phrasings must exactly equal frozen W1 pairs')
    pair_file = json.loads((bank / 'pairs.json').read_text())
    continued = {f: [(p['A'], p['B']) for p in pair_file['rows'][f]['pairs']] for f in FEATURES}
    if any(continued[f] != list(PAIRS[f]) for f in FEATURES):
        raise ValueError('E15 continuation pairs changed')
    if any(len(asked[f]) != 2 or len(continued[f]) != 2 for f in FEATURES):
        raise ValueError('exact two frozen pairs per channel required')
    return items, asked, continued


def capture_source(oracle, items, capture_fn=None):
    """Actual target residual at each read token; no following token is forwarded."""
    import torch
    if capture_fn is None:
        from mats.capture import capture as capture_fn
    if any(x['read_index'] != len(x['ids']) - 1 for x in items):
        raise ValueError('source input must end at the read token')
    with oracle.base():
        h = capture_fn(oracle.model, [x['ids'] for x in items], [44],
                       [[x['read_index']] for x in items], batch_size=CAPTURE_BATCH,
                       pad_id=oracle.tok.pad_token_id or 0)[44]
    if h.ndim != 3 or h.shape[:2] != (len(items), 1) or not torch.isfinite(h).all():
        raise ValueError('invalid block-44 capture')
    return h[:, 0].float().cpu()


def window_texts(tok, items):
    """No prefix/captured token, generation, padding or truncation enters the AR."""
    texts = []
    for x in items:
        ids = x['next16_ids']
        if len(ids) != 16:
            raise ValueError('real next16 window must contain exactly 16 tokens')
        text = tok.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if text != x['next16_text'] or tok.encode(text, add_special_tokens=False) != ids:
            raise ValueError('AR decode/retokenize changes the frozen real next16 IDs')
        texts.append(text)
    return texts


def reconstruct_window(ar, tok, items, reconstruct_fn=None):
    if reconstruct_fn is None:
        from projects.g_agreement.w_claims.ar import reconstruct as reconstruct_fn
    return reconstruct_fn(ar, tok, window_texts(tok, items))


def score_channel(oracle, h, pairs, channel):
    if channel == 'continuation':
        return native_score('olens', oracle, h, pairs)
    if channel == 'asked':
        return oracle.paired_logodds_templates(h, 44, pairs)
    raise ValueError('unknown E17 scoring channel')


def donor_records(items, true_records):
    """Reindex fixed donor activations' identical-prompt scores; never flip signs."""
    lookup = {(r['id'], r['channel']): r for r in true_records}
    expected = {(x['id'], c) for x in items for c in CHANNELS}
    if len(lookup) != len(true_records) or set(lookup) != expected:
        raise ValueError('complete unique true-score grid required before donor controls')
    records = list(true_records)
    for x in items:
        for channel in CHANNELS:
            for arm, key in (('random_donor', 'random_donor_id'), ('opposite_swap', 'opposite_donor_id')):
                source = lookup[x[key], channel]
                if source['feature'] != x['feature']:
                    raise ValueError('donor score used another row prompt')
                records.append({**source, 'id': x['id'], 'cell': x['cell'],
                                'arm': arm, 'donor_id': x[key]})
    return records


def validate_grid(items, records):
    expected = {(x['id'], c, a) for x in items for c in CHANNELS for a in ARMS}
    keys = [(r['id'], r['channel'], r['arm']) for r in records]
    if (len(keys) != len(set(keys)) or set(keys) != expected
            or any(r['status'] != 'COMPLETE' or len(r['scores']) != 2
                   or not np.isfinite(r['scores']).all() for r in records)):
        raise ValueError('incomplete or nonfinite E17 score grid')


def forecast_allocation(elapsed, remaining):
    if not all(math.isfinite(x) and x >= 0 for x in (elapsed, remaining)):
        raise ValueError('invalid warmed forecast')
    forecast = elapsed + remaining
    allocation = min(1.5 * forecast + 360, CAP)
    return {'forecast_s': forecast, 'remaining_s': remaining,
            'allocation_s': allocation, 'fits': forecast <= allocation}


def admit(assignment, bank, *, now=None, pod_id=None):
    a = json.loads(Path(assignment).read_text())
    now = time.time() if now is None else now
    pod_id = os.environ.get('RUNPOD_POD_ID') if pod_id is None else pod_id
    if (a.get('issuer') != 'integrator' or a.get('experiment') != 'E17'
            or not pod_id or a.get('pod_id') != pod_id):
        raise ValueError('exact E17 integrator assignment required')
    if any(a.get(k) is not True for k in
           ('brief_registered', 'brief_pushed', 'manifest_committed', 'external_hardstop_verified')):
        raise ValueError('published registration, committed bank and external guard required')
    if (a.get('source_files') != source_hashes()
            or a.get('manifest_sha256') != P.sha(Path(bank) / 'manifest.json')
            or a.get('input_seal_sha256') != P.sha(Path(bank) / 'INPUT_SEAL.json')):
        raise ValueError('exact committed source and bank binding required')
    manifest = json.loads((Path(bank) / 'manifest.json').read_text())
    if (manifest.get('experiment') != 'E17' or manifest.get('section') != 110
            or not a.get('brief_commit', '').startswith(manifest.get('registration_commit', '!'))):
        raise ValueError('assignment does not bind E17 section110 registration')
    for name, digest in manifest.get('authoring_sources', {}).items():
        if (Path(name).is_absolute() or '..' in Path(name).parts
                or P.sha(P.ROOT / name) != digest):
            raise ValueError('item authoring source changed: ' + name)
    for field in ('source_commit', 'manifest_commit', 'brief_commit'):
        value = a.get(field, '')
        if len(value) != 40 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('full commit required: ' + field)
    created = float(a['provider_created_epoch'])
    deadline = float(a['deadline_epoch'])
    allocated = float(a['allocated_gpu_seconds'])
    if (a.get('previous_gpu_seconds') != 0 or a.get('science_cap_gpu_seconds') != CAP
            or a.get('staging_allowance_seconds') != SETUP
            or not all(math.isfinite(x) for x in (now, created, deadline, allocated))
            or not created <= now < min(created + SETUP, deadline - RETRIEVAL_RESERVE)
            or not 0 < deadline - created <= allocated):
        raise ValueError('expired/invalid E17 setup, cap or custody; no retries')
    return a


class Guard:
    """One persistent science clock; setup, science and retrieval deadlines are absolute."""
    def __init__(self, assignment, out):
        self.assignment = assignment
        self.out = Path(out)
        self.first = None
        self.absolute = float(assignment['deadline_epoch']) - RETRIEVAL_RESERVE
        self.end = min(float(assignment['provider_created_epoch']) + SETUP, self.absolute)
        self.old_handler = signal.signal(signal.SIGALRM, self.expired)
        self.check()

    def expired(self, *_):
        raise TimeoutError('E17 setup/science/absolute deadline reached')

    def check(self):
        remaining = self.end - time.time()
        if remaining <= 0:
            self.expired()
        signal.setitimer(signal.ITIMER_REAL, max(.001, remaining))

    def start(self):
        if self.first is not None:
            raise RuntimeError('E17 science clock cannot restart')
        self.check()
        self.first = time.time()
        with (self.out / 'EXPERIMENT_CLOCK.json').open('x') as stream:
            json.dump({'experiment': 'E17', 'first_science_epoch': self.first}, stream)
        self.end = min(self.first + CAP, self.absolute)
        self.check()

    def tighten(self, allocation):
        if self.first is None:
            raise RuntimeError('science clock has not started')
        self.end = min(self.end, self.first + allocation)
        self.check()

    def finish(self):
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, self.old_handler)
        P.dump(self.out / 'SCIENCE_RECEIPT.json', {
            'experiment': 'E17', 'first_science_epoch': self.first,
            'completed_epoch': time.time(),
            'science_elapsed_s': 0 if self.first is None else time.time() - self.first,
            'effective_deadline_epoch': self.end, 'science_ceiling_s': CAP,
            'setup_allowance_s': SETUP, 'no_automatic_retry': True})


def _timed(fn):
    import torch
    torch.cuda.synchronize()
    start = time.perf_counter()
    result = fn()
    torch.cuda.synchronize()
    return result, time.perf_counter() - start


def _move(module, device):
    """Keep checkpoints alive; residency transfer is counted, never a fresh load."""
    import torch
    if device == 'cpu' and Path('/proc/meminfo').exists():
        info = {r.split(':')[0]: int(r.split()[1]) * 1024
                for r in Path('/proc/meminfo').read_text().splitlines()
                if len(r.split()) > 1 and r.split()[1].isdigit()}
        need = sum(p.numel() * p.element_size() for p in module.parameters() if p.device.type == 'cuda')
        if info.get('MemAvailable', 0) < need + 8 * 1024**3:
            raise MemoryError('insufficient host RAM for persistent model residency')
    module.to(device)
    if device == 'cpu':
        gc.collect()
        torch.cuda.empty_cache()


def _chunks(indices, size):
    return [indices[i:i + size] for i in range(0, len(indices), size)]


def run(a):
    import torch
    items, asked, continued = inputs(a.bank)
    assignment = admit(a.assignment, a.bank)
    a.out.mkdir(parents=True, exist_ok=False)
    guard = Guard(assignment, a.out)
    status = 'INCOMPLETE'
    try:
        # Both load calls occur only within setup. The official AR helper is the
        # exact E1b path: unwhitened layer-44 vectors, no prefix conditioning.
        from projects.g_agreement.blindspot.ar_tests import _assets as ar_assets
        from projects.g_agreement.w_claims.ar import load_reconstructor
        assets = W._assets(a.assets, names=('model', 'olens'))
        ar_assets(a.assets, ('ar',))
        guard.check()
        oracle = W._load_oracle(assets)
        cells = sorted({(x['feature'], x['cell']) for x in items})
        by_cell = {c: [i for i, x in enumerate(items) if (x['feature'], x['cell']) == c] for c in cells}
        by_feature = {f: [i for i, x in enumerate(items) if x['feature'] == f] for f in FEATURES}
        # Fixed canonical batches. Capture warm-up uses the longest prefixes.
        worst = sorted(range(len(items)), key=lambda i: (-len(items[i]['ids']), items[i]['id']))[:CAPTURE_BATCH]
        warm_h = capture_source(oracle, [items[i] for i in worst])
        warm_scores = warm_h.repeat(math.ceil(SCORE_BATCH / len(warm_h)), 1)[:SCORE_BATCH]
        for f in FEATURES:
            for channel, pairs in (('continuation', continued[f]), ('asked', asked[f])):
                score_channel(oracle, warm_scores, pairs, channel)
                guard.check()
        _move(oracle.model, 'cpu')
        oracle.device = 'cpu'
        guard.check()
        ar, ar_tok, _ = load_reconstructor(a.official, a.whitener, assets['ar'], assets['model'])
        window_texts(ar_tok, items)  # Reject every retokenization mismatch before science.
        reconstruct_window(ar, ar_tok, items[:AR_BATCH])
        guard.check()
        _move(ar, 'cpu')
        _move(oracle.model, 'cuda')
        oracle.device = 'cuda'
        guard.check()
        guard.start()

        # Freeze deterministic unit partitions before retained acquisition.
        # Source units are ordered longest-first within each cell. A score unit
        # contains exactly 32 real items from the matching feature, never repeats.
        capture_units = {c: _chunks(sorted(by_cell[c], key=lambda i:
                         (-len(items[i]['ids']), items[i]['id'])), CAPTURE_BATCH) for c in cells}
        capture_keys = [(c, k) for c in cells for k in range(len(capture_units[c]))]
        key_number = {key: n for n, key in enumerate(capture_keys)}
        capture_for_index = {i: (c, k) for c, k in capture_keys for i in capture_units[c][k]}
        score_units = {f: _chunks([i for c in cells if c[0] == f
                       for unit in capture_units[c] for i in unit], SCORE_BATCH) for f in FEATURES}
        window_units = _chunks(list(range(len(items))), AR_BATCH)
        unit_plan = {'capture44': [{'unit': key_number[c, k], 'feature': c[0], 'cell': c[1],
                                  'indices': capture_units[c][k]} for c, k in capture_keys],
                     'scores': {f: score_units[f] for f in FEATURES}, 'window44': window_units}
        P.dump(a.out / 'unit_plan.json', unit_plan)
        (a.out / 'units').mkdir()
        vectors = [None] * len(items)
        windows = [None] * len(items)
        capture_done = set()
        score_done = set()
        window_done = set()
        measured = defaultdict(list)
        records = []

        def capture_unit(key):
            if key in capture_done:
                raise RuntimeError('duplicate retained E17 capture unit')
            c, k = key
            ix = capture_units[c][k]
            guard.check()
            h, seconds = _timed(lambda: capture_source(oracle, [items[i] for i in ix]))
            np.save(a.out / 'units' / f'capture-{key_number[key]:04d}.npy', h.numpy(), allow_pickle=False)
            for i, row in zip(ix, h):
                vectors[i] = row.numpy()
            capture_done.add(key)
            measured['capture44', c].append(seconds)

        def score_unit(f, channel, k):
            key = f, channel, k
            if key in score_done:
                raise RuntimeError('duplicate retained E17 score unit')
            ix = score_units[f][k]
            if any(vectors[i] is None for i in ix):
                raise RuntimeError('source capture prerequisite is missing')
            pairs = continued[f] if channel == 'continuation' else asked[f]
            h = torch.from_numpy(np.stack([vectors[i] for i in ix]))
            guard.check()
            values, seconds = _timed(lambda: score_channel(oracle, h, pairs, channel))
            if tuple(values.shape) != (2, len(ix)) or not torch.isfinite(values).all():
                raise ValueError('invalid E17 Oracle paired scores')
            for j, i in enumerate(ix):
                x = items[i]
                row = {'id': x['id'], 'feature': f, 'cell': x['cell'], 'channel': channel,
                       'reader': 'olens', 'layer': 44, 'arm': 'true',
                       'scores': values[:, j].tolist(), 'status': 'COMPLETE'}
                records.append(row)
                with (a.out / 'scores.partial.jsonl').open('a') as stream:
                    stream.write(json.dumps(row, sort_keys=True) + '\n')
                    stream.flush()
            score_done.add(key)
            measured[channel, f].append(seconds)

        def window_unit(k):
            if k in window_done:
                raise RuntimeError('duplicate retained E17 AR unit')
            ix = window_units[k]
            guard.check()
            value, seconds = _timed(lambda: reconstruct_window(ar, ar_tok, [items[i] for i in ix]))
            width = next(v.shape[0] for v in vectors if v is not None)
            if tuple(value.shape) != (len(ix), width) or not torch.isfinite(value).all():
                raise ValueError('invalid E17 AR window vectors')
            np.save(a.out / 'units' / f'window-{k:04d}.npy', value.numpy(), allow_pickle=False)
            for i, row in zip(ix, value):
                windows[i] = row.numpy()
            window_done.add(k)
            measured['window44'].append(seconds)

        # Every timing result below is a real, retained production result.
        # Additional prerequisite captures are also retained and charged; no
        # canonical capture, score or AR unit is run again after admission.
        for c in cells:
            for k in range(3):
                capture_unit((c, k))
        for f in FEATURES:
            required_keys = {capture_for_index[i] for unit in score_units[f][:3] for i in unit}
            for key in sorted(required_keys, key=lambda key: key_number[key]):
                if key not in capture_done:
                    capture_unit(key)
            for channel in CHANNELS:
                for k in range(3):
                    score_unit(f, channel, k)
        guard.check()
        movement_start = time.perf_counter()
        _move(oracle.model, 'cpu')
        oracle.device = 'cpu'
        _move(ar, 'cuda')
        to_ar_seconds = time.perf_counter() - movement_start
        for k in range(3):
            window_unit(k)
        _move(ar, 'cpu')
        _move(oracle.model, 'cuda')
        oracle.device = 'cuda'
        guard.check()

        remaining = to_ar_seconds
        timings = []
        for c in cells:
            times = measured['capture44', c][:3]
            count = sum((c, k) not in capture_done for k in range(len(capture_units[c])))
            remaining += statistics.median(times) * count
            timings.append({'phase': 'capture44', 'feature': c[0], 'cell': c[1],
                            'warmed_units_s': times, 'remaining_units': count,
                            'retained_units': len(capture_units[c]) - count})
        for f in FEATURES:
            for channel in CHANNELS:
                times = measured[channel, f][:3]
                count = sum((f, channel, k) not in score_done for k in range(len(score_units[f])))
                remaining += statistics.median(times) * count
                timings.append({'phase': channel, 'feature': f, 'warmed_units_s': times,
                                'remaining_units': count, 'retained_units': len(score_units[f]) - count})
        times = measured['window44'][:3]
        count = len(window_units) - len(window_done)
        remaining += statistics.median(times) * count
        timings.append({'phase': 'real_next16_ar44', 'warmed_units_s': times,
                        'remaining_units': count, 'retained_units': len(window_done)})
        forecast = forecast_allocation(time.time() - guard.first, remaining)
        forecast.update({'timings': timings, 'future_residency_transfer_s': to_ar_seconds,
                         'timing_outputs_retained': True, 'full_scope': True,
                         'unit_plan_sha256': P.sha(a.out / 'unit_plan.json')})
        fits = forecast['fits'] and time.time() + remaining <= min(guard.end, guard.first + forecast['allocation_s'])
        forecast['status'] = 'FIT' if fits else 'NO_FIT'
        P.dump(a.out / 'FORECAST.json', forecast)
        if not fits:
            status = 'NO_FIT'
            P.dump(a.out / 'STATUS.json', {'status': status, 'scope_reduced': False})
            return
        guard.tighten(forecast['allocation_s'])

        for key in capture_keys:
            if key not in capture_done:
                capture_unit(key)
        source = np.stack(vectors)
        np.save(a.out / 'source44.npy', source, allow_pickle=False)
        P.dump(a.out / 'items.order.json', [x['id'] for x in items])
        P.dump(a.out / 'CAPTURE_SEAL.json', {'status': 'E17_SOURCE44_CAPTURE_COMPLETE',
               'files': {n: P.sha(a.out / n) for n in ('source44.npy', 'items.order.json')},
               'input_seal_sha256': P.sha(a.bank / 'INPUT_SEAL.json')})
        for f in FEATURES:
            for channel in CHANNELS:
                for k in range(len(score_units[f])):
                    if (f, channel, k) not in score_done:
                        score_unit(f, channel, k)
        guard.check()
        _move(oracle.model, 'cpu')
        oracle.device = 'cpu'
        _move(ar, 'cuda')
        for k in range(len(window_units)):
            if k not in window_done:
                window_unit(k)
        np.save(a.out / 'window44.npy', np.stack(windows), allow_pickle=False)
        records = donor_records(items, records)
        validate_grid(items, records)
        P.jsonl(a.out / 'scores.jsonl', records)
        P.dump(a.out / 'provenance.json', {
            'experiment': 'E17', 'input_seal_sha256': P.sha(a.bank / 'INPUT_SEAL.json'),
            'manifest_sha256': P.sha(a.bank / 'manifest.json'), 'source_files': source_hashes(),
            'assignment_sha256': P.sha(a.assignment), 'assets_sha256': P.sha(a.assets),
            'capture_block': 44, 'capture_input': 'prefix through read token only; adapter disabled',
            'window': 'frozen real next16 tokens, exact decode-retokenize identity, E1b unchanged AR',
            'source_and_window_probes': 'pending CPU dev-only fit after seal; no fit in worker',
            'donors': 'frozen same-row/cell/split score reindexing; no sign flips',
            'checkpoint_load_counts': {'target_and_oracle_shared_backbone': 1, 'AR': 1},
            'scoring_policy': {'continuation_prefix': '- ', 'asked': 'unchanged W1 native pairs'},
            'batch_sizes': {'capture': CAPTURE_BATCH, 'scoring': SCORE_BATCH, 'AR': AR_BATCH}})
        guard.check()
        status = 'E17_CHANNELS_SEALED_BEFORE_LABEL_JOIN'
        names = ('source44.npy', 'window44.npy', 'items.order.json', 'scores.jsonl',
                 'provenance.json', 'FORECAST.json', 'EXPERIMENT_CLOCK.json', 'CAPTURE_SEAL.json', 'unit_plan.json')
        P.dump(a.out / 'SCORE_SEAL.json', {'status': status, 'files': {n: P.sha(a.out / n) for n in names}})
        P.dump(a.out / 'STATUS.json', {'status': status, 'scope_reduced': False})
    except Exception as exc:
        P.dump(a.out / 'FAILURE.json', {'status': 'INCOMPLETE', 'error_type': type(exc).__name__,
               'reason': str(exc), 'no_automatic_retry': True})
        raise
    finally:
        guard.finish()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('bank', 'assignment', 'assets', 'official', 'whitener', 'out'):
        p.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    with P.logged('e17_horizon_capture_and_channels', gpu=True, extra={'cap_seconds': CAP, 'setup_seconds': SETUP}):
        run(a)


if __name__ == '__main__':
    main()
