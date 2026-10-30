"""Remainder R5 / BRIEF_R §23. Prepare-only native Oracle gain/site sweep.

preflight and --mock smoke are CPU-only. Live scoring is explicitly gated and
never allocates a pod. Source cache is read-only; experiment outputs are isolated.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench import interim as I

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / 'cache/g_agreement/r/remainder/r5'
RESULTS = ROOT / 'results/g_agreement/r/remainder/r5'
BANK = ROOT / 'projects/g_agreement/dataset/items_r.json'
STATES = ROOT / 'cache/g_agreement/r/states'
FREEZE = ROOT / 'projects/g_agreement/manifest/frozen_config_r.json'
GAINS = (.5, 1., 2., 4.)
LAYERS = (36, 40, 44, 48)
ARMS = ('natural', 'shuffled')
SETTINGS = [(layer, gain, arm) for layer in LAYERS for gain in GAINS for arm in ARMS]
DEFAULT = (44, 1., 'natural')
SEED = 20261020
N_FACTS, N_TEST, N_POOL = 20, 200, 64
EXPECTED_ROWS = N_FACTS * (N_TEST + N_POOL) * len(SETTINGS)
PULL_RESERVE = 300


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n')


def code_hash():
    # Shared scorer/config/model changes invalidate a live smoke, too.
    paths = [Path(__file__), ROOT/'projects/g_agreement/r_bench/collect.py',
             ROOT/'projects/g_agreement/core/readers.py', ROOT/'projects/g_agreement/core/scoring_lo.py',
             ROOT/'projects/g_agreement/core/config.py', ROOT/'projects/g_agreement/core/model.py']
    return digest({str(p.relative_to(ROOT)): sha(p) for p in paths})


def metadata(pod):
    proc = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    git_sha = proc.stdout.strip() if proc.returncode == 0 else os.environ.get('R_GIT_SHA', '')
    if not git_sha and (ROOT/'GIT_SHA').exists():
        git_sha = (ROOT/'GIT_SHA').read_text().strip()
    if not git_sha:
        raise ValueError('Missing git SHA; write GIT_SHA to the isolated pod repo')
    return {'pod': pod, 'git_sha': git_sha, 'code_sha': code_hash(),
            'created_at': datetime.now(timezone.utc).isoformat()}


def select_items(items, n_facts=N_FACTS, n_test=N_TEST, n_pool=N_POOL):
    """Selection reads labels/counts only, never reader/model outcomes or availability."""
    if n_test % 2 or n_pool % 2:
        raise ValueError('Balanced split sizes must be even')
    groups = defaultdict(list)
    for item in items:
        groups[item['dataset']].append(item)
    tags = defaultdict(list)
    for ds, rows in groups.items():
        if ds in I.LABEL_DEFECT:
            continue
        if {r['label'] for r in rows} != {0, 1}:
            continue
        if len({r['tag'] for r in rows}) != 1:
            raise ValueError(f'{ds}: conflicting tags')
        counts = Counter((r['split'], r['label']) for r in rows)
        if any(counts[(split, y)] < n//2 for split, n in [('test', n_test), ('pool', n_pool)] for y in (0, 1)):
            continue
        tags[rows[0]['tag']].append(ds)
    for tag in tags:
        tags[tag].sort(key=lambda ds: hashlib.sha256(f'{SEED}|{ds}'.encode()).hexdigest())
    facts = []
    for k in range(max(map(len, tags.values()), default=0)):
        for tag in sorted(tags):
            if k < len(tags[tag]):
                facts.append(tags[tag][k])
                if len(facts) == n_facts:
                    break
        if len(facts) == n_facts:
            break
    if len(facts) != n_facts:
        raise ValueError(f'Need {n_facts} eligible facts, found {len(facts)}')
    selected = []
    for ds in facts:
        rows = groups[ds]
        for split, n in [('pool', n_pool), ('test', n_test)]:
            for y in (0, 1):
                selected.extend(sorted((r for r in rows if r['split'] == split and r['label'] == y),
                                       key=lambda r: r['item_id'])[:n//2])
    return selected


def derangement(ids, key):
    ids = list(ids)
    if len(ids) < 2:
        raise ValueError('Cannot shuffle fewer than two states')
    rng = np.random.default_rng(int(hashlib.sha256(f'{SEED}|{key}'.encode()).hexdigest()[:16], 16))
    ix = np.arange(len(ids))
    for _ in range(10000):
        perm = rng.permutation(len(ids))
        if np.all(perm != ix):
            return dict(zip(ids, [ids[i] for i in perm]))
    raise RuntimeError('Failed to construct deterministic derangement')


def make_manifest(items, bank_path=BANK, states_dir=STATES, freeze_path=FREEZE,
                  n_facts=N_FACTS, n_test=N_TEST, n_pool=N_POOL):
    frozen = json.loads(freeze_path.read_text())
    bank_sha = sha(bank_path)
    if frozen['items_sha256'].get(bank_path.name) != bank_sha:
        raise ValueError('Frozen bank hash mismatch')
    selected = select_items(items, n_facts, n_test, n_pool)
    by_ds = defaultdict(list)
    for it in selected:
        by_ds[it['dataset']].append(it)
    facts, errors = [], []
    for ds, group in by_ds.items():
        entry = {'dataset': ds, 'tag': group[0]['tag'], 'corpus': I.corpus_of(ds),
                 'states': {}, 'items': [], 'source_index_provenance': {}}
        ip = states_dir/ds/'index.json'
        if not ip.exists():
            errors.append(f'{ds}: missing index.json')
            continue
        index = json.loads(ip.read_text())
        ids = index['item_ids']
        if len(ids) != len(set(ids)):
            raise ValueError(f'{ds}: duplicate source state IDs')
        if any(len(index.get(key, [])) != len(ids) for key in ('labels', 'splits')):
            raise ValueError(f'{ds}: source index lacks complete labels/splits')
        if 'chat' not in index.get('renders', []):
            raise ValueError(f'{ds}: source index does not declare chat render')
        lookup = {v: j for j, v in enumerate(ids)}
        entry['index_sha256'] = sha(ip)
        entry['source_index_provenance'] = {k: index.get(k) for k in ('pod', 'git_sha', 'created_at', 'state_dtype', 'renders', 'max_tokens')}
        donors = {}
        for split in ('pool', 'test'):
            split_ids = sorted(it['item_id'] for it in group if it['split'] == split)
            donors.update(derangement(split_ids, f'{ds}|{split}'))
        for it in sorted(group, key=lambda x: (x['split'], x['item_id'])):
            iid = it['item_id']
            if iid not in lookup:
                errors.append(f'{ds}: missing state ID {iid}')
                continue
            j = lookup[iid]
            if index['labels'][j] != it['label'] or index['splits'][j] != it['split']:
                errors.append(f'{ds}: source index label/split mismatch {iid}')
            entry['items'].append({'item_id': iid, 'split': it['split'], 'label': it['label'],
                                   'text_hash': hashlib.sha256(it['prompt_text'].encode()).hexdigest(),
                                   'item_sha256': digest(it), 'state_row': j, 'donor_item_id': donors[iid],
                                   'donor_state_row': lookup[donors[iid]]})
        for layer in LAYERS:
            sp = states_dir/ds/f'chat_L{layer}.npy'
            if not sp.exists():
                errors.append(f'{ds}: missing chat_L{layer}.npy')
                continue
            arr = np.load(sp, mmap_mode='r')
            if arr.ndim != 2 or len(arr) != len(ids) or arr.shape[1] != C.D_MODEL:
                errors.append(f'{ds}: invalid shape {arr.shape} at L{layer}')
                continue
            selected_rows = [x['state_row'] for x in entry['items']]
            if not np.isfinite(arr[selected_rows]).all() or np.any(np.linalg.norm(arr[selected_rows].astype(float), axis=1) == 0):
                errors.append(f'{ds}: nonfinite/zero selected state at L{layer}')
            entry['states'][str(layer)] = {'sha256': sha(sp), 'shape': list(arr.shape), 'dtype': str(arr.dtype)}
        facts.append(entry)
    return {'schema': 1, 'bank_sha256': bank_sha, 'freeze_sha256': sha(freeze_path), 'facts': facts,
            'selection_seed': SEED, 'gains': list(GAINS), 'layers': list(LAYERS), 'arms': list(ARMS),
            'default': list(DEFAULT), 'base_alpha': C.OLENS_ALPHA, 'errors': errors,
            'n_test': n_test, 'n_pool': n_pool, 'n_facts': n_facts,
            'expected_rows': n_facts*(n_test+n_pool)*len(SETTINGS)}


def freeze_manifest(manifest, path):
    if manifest['errors']:
        raise ValueError('PREFLIGHT FAILED: ' + '; '.join(manifest['errors']))
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise ValueError('Frozen manifest changed; do not overwrite or silently reselect')
    write_json(path, manifest)


@contextmanager
def insertion_gain(reader, gain, default_alpha):
    original = reader.alpha
    try:
        reader.alpha = default_alpha*gain
        yield reader
    finally:
        reader.alpha = original


def validate_guard_record(record, pod, deadline_epoch, now):
    """Bind the budget to the original shared hard-stop, never a fresh relative cap."""
    if record.get('pod') != pod or record.get('experiment') != 'r5':
        raise ValueError('Shared guard record has wrong pod or experiment')
    values = (record.get('started_epoch'), record.get('deadline_epoch'), deadline_epoch, now)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) for v in values):
        raise ValueError('Shared guard record/deadline has invalid epoch')
    started, original_deadline, deadline_epoch, now = values
    if started > now or not 0 < original_deadline-started <= 1800:
        raise ValueError('Shared guard record exceeds the original 0.5 pod-hour cap')
    if deadline_epoch > original_deadline:
        raise ValueError('Requested deadline renews the original hard-stop budget')
    if deadline_epoch-now <= PULL_RESERVE:
        raise ValueError('No remaining budget after audit/pull reserve')


def live_authorized(pod, deadline_epoch):
    own = None
    proc = Path('/proc/1/environ')
    if proc.exists():
        for field in proc.read_bytes().split(b'\0'):
            if field.startswith(b'RUNPOD_POD_ID='):
                own = field.split(b'=', 1)[1].decode()
    if own != pod:
        raise ValueError(f'POD ID MISMATCH: intended {pod}; refused live scoring')
    # Shared remainder_pod bootstrap is the only guard implementation.
    run_dir = ROOT.parent
    record_path = run_dir/'guard.json'
    if not record_path.exists():
        raise ValueError('Shared guard bootstrap guard.json absent')
    validate_guard_record(json.loads(record_path.read_text()), pod, deadline_epoch, time.time())
    if not (run_dir/'ARMED').exists():
        raise ValueError('Shared guard bootstrap ARMED marker absent')
    for name in ('watchdog', 'hardstop'):
        if 'armed:' not in (run_dir/f'{name}.log').read_text():
            raise ValueError(f'{name} did not log armed')
        os.kill(int((run_dir/f'{name}.pid').read_text()), 0)


def row_key(ds, iid, layer, gain, arm):
    return f'{ds}|{iid}|L{layer}|g{gain:g}|{arm}'


def smoke_items(fact):
    return [next(it for it in fact['items'] if it['split'] == split and it['label'] == y)
            for split in ('pool', 'test') for y in (0, 1)]


def assert_coverage(rows, manifest, smoke=False):
    expected = {}
    manifest_sha = digest(manifest)
    for fact in manifest['facts']:
        for it in smoke_items(fact) if smoke else fact['items']:
            for layer, gain, arm in SETTINGS:
                key = row_key(fact['dataset'], it['item_id'], layer, gain, arm)
                expected[key] = (fact, it, layer, gain, arm)
    seen = set()
    for row in rows:
        key = row['key']
        if key in seen:
            raise ValueError(f'SMOKE FAILED: duplicate {key}')
        if key not in expected:
            raise ValueError(f'SMOKE FAILED: unexpected {key}')
        fact, it, layer, gain, arm = expected[key]
        for field, value in [('dataset', fact['dataset']), ('item_id', it['item_id']), ('split', it['split']),
                             ('label', it['label']), ('layer', layer), ('gain', gain), ('arm', arm)]:
            if row.get(field) != value:
                raise ValueError(f'SMOKE FAILED: {key} inconsistent {field}')
        if row.get('state_item_id') != (it['item_id'] if arm == 'natural' else it['donor_item_id']):
            raise ValueError(f'SMOKE FAILED: {key} incorrect donor')
        if row.get('lo') is None or not np.isfinite(row['lo']) or row.get('score') is None or not np.isfinite(row['score']):
            raise ValueError(f'SMOKE FAILED: nonfinite {key}')
        if any(not row.get(k) for k in ('pod', 'git_sha', 'code_sha', 'manifest_sha')):
            raise ValueError(f'SMOKE FAILED: missing provenance {key}')
        if row['manifest_sha'] != manifest_sha:
            raise ValueError(f'SMOKE FAILED: manifest mismatch {key}')
        if row.get('alpha') != gain*manifest['base_alpha'] or row.get('layer_in_prompt') != layer:
            raise ValueError(f'SMOKE FAILED: native insertion/carrier mismatch {key}')
        seen.add(key)
    missing = set(expected)-seen
    if missing:
        raise ValueError(f'SMOKE FAILED: missing {len(missing)} rows; first {sorted(missing)[0]}')
    return len(seen)


def collect_scores(manifest, items_by_id, reader, scorer, meta, path, smoke=False,
                   states_dir=STATES, batch=32, deadline_epoch=None):
    """Dependency-injected scorer enables CPU contract tests; live uses collect.score_items."""
    if path.exists():
        raise ValueError(f'Refuse existing output {path}; use a fresh run or audit it')
    rows, timing = [], []
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_sha = digest(manifest)
    with path.open('x') as stream:
        for fact in manifest['facts']:
            tick = time.monotonic()
            n_written = 0
            chosen = smoke_items(fact) if smoke else fact['items']
            for layer in LAYERS:
                X = np.load(states_dir/fact['dataset']/f'chat_L{layer}.npy', mmap_mode='r')
                for gain in GAINS:
                    for arm in ARMS:
                        for start in range(0, len(chosen), max(1, batch//2)):
                            if deadline_epoch is not None and time.time()+PULL_RESERVE >= deadline_epoch:
                                raise RuntimeError('BUDGET STOP: audit/pull reserve reached; incomplete population')
                            chunk = chosen[start:start+max(1, batch//2)]
                            H = np.asarray(X[[it['state_row'] if arm == 'natural' else it['donor_state_row'] for it in chunk]], dtype=np.float32)
                            its = [items_by_id[it['item_id']] for it in chunk]
                            with insertion_gain(reader, gain, manifest['base_alpha']):
                                scored = scorer(reader, H, its, layer, batch)
                            if len(scored) != len(chunk):
                                raise RuntimeError('SMOKE FAILED: scorer dropped items')
                            for it, score in zip(chunk, scored):
                                row = {**meta, 'key': row_key(fact['dataset'], it['item_id'], layer, gain, arm),
                                       'manifest_sha': manifest_sha, 'dataset': fact['dataset'], 'tag': fact['tag'],
                                       'corpus': fact['corpus'], 'item_id': it['item_id'], 'split': it['split'],
                                       'label': it['label'], 'text_hash': it['text_hash'], 'layer': layer,
                                       'gain': gain, 'alpha': gain*manifest['base_alpha'], 'arm': arm,
                                       'state_item_id': it['item_id'] if arm == 'natural' else it['donor_item_id'],
                                       'render': 'chat', 'position': 'last', 'reader': 'olens', 'mock': bool(meta.get('mock')),
                                       'lo': score['lo'], 'lp_A': score.get('lp_A'), 'lp_B': score.get('lp_B'),
                                       'score': score.get('lp_A') if items_by_id[it['item_id']]['primary'].get('sided') == 'one' else score['lo'],
                                       'score_kind': 'lp_A' if items_by_id[it['item_id']]['primary'].get('sided') == 'one' else 'lo',
                                       'n_tokens_A': score.get('n_tokens_A'), 'n_tokens_B': score.get('n_tokens_B'),
                                       'layer_in_prompt': score.get('layer_in_prompt', layer)}
                                stream.write(json.dumps(row, allow_nan=False)+'\n')
                                rows.append(row)
                            stream.flush()
                            n_written += len(chunk)
            elapsed = time.monotonic()-tick
            timing.append({'dataset': fact['dataset'], 'rows': n_written, 'candidate_sequences': 2*n_written,
                           'seconds': elapsed, 'seconds_per_sequence': elapsed/(2*n_written)})
            print(f"R5 {'smoke' if smoke else 'run'} {fact['dataset']}: {n_written} rows in {elapsed:.1f}s", flush=True)
    assert_coverage(rows, manifest, smoke=smoke)
    return rows, timing


def throughput_gate(certificate, manifest, meta, deadline_epoch, batch):
    if certificate.get('mock') is not False or certificate.get('live') is not True:
        raise ValueError('CPU mock is not a live smoke certificate')
    for key, expected in [('manifest_sha', digest(manifest)), ('code_sha', meta['code_sha']),
                          ('git_sha', meta['git_sha']), ('pod', meta['pod']), ('batch', batch),
                          ('deadline_epoch', deadline_epoch)]:
        if certificate.get(key) != expected:
            raise ValueError(f'Live smoke certificate differs: {key}')
    if certificate.get('coverage_rows') != manifest['n_facts']*4*len(SETTINGS):
        raise ValueError('Live smoke coverage is incomplete')
    slowest = max(t['seconds_per_sequence'] for t in certificate['timing'])
    projected = 1.5*slowest*manifest['expected_rows']*2
    remaining = deadline_epoch-time.time()
    if not np.isfinite(projected) or projected <= 0 or projected+PULL_RESERVE > remaining:
        raise ValueError(f'THROUGHPUT BLOCKED: full grid projects {projected:.1f}s + {PULL_RESERVE}s reserve; {remaining:.1f}s left. No downsampling.')
    return {'projected_collection_seconds': projected, 'remaining_seconds': remaining,
            'reserve_seconds': PULL_RESERVE, 'full_candidate_sequences': manifest['expected_rows']*2}


def weighted_auc(y, scores, weights):
    """All score columns × bootstrap weights, preserving ties and common draws."""
    y, scores, weights = np.asarray(y), np.asarray(scores), np.asarray(weights, float)
    if weights.ndim == 1:
        weights = weights[None]
    if scores.ndim == 1:
        scores = scores[:, None]
    out = np.empty((len(weights), scores.shape[1]))
    for col in range(scores.shape[1]):
        order = np.argsort(scores[:, col], kind='stable')
        sorted_s = scores[order, col]
        starts = np.r_[0, np.flatnonzero(np.diff(sorted_s))+1]
        pos = np.add.reduceat(weights[:, order]*(y[order] == 1), starts, axis=1)
        neg = np.add.reduceat(weights[:, order]*(y[order] == 0), starts, axis=1)
        denom = pos.sum(axis=1)*neg.sum(axis=1)
        with np.errstate(invalid='ignore', divide='ignore'):
            out[:, col] = (pos*(np.cumsum(neg, axis=1)-.5*neg)).sum(axis=1)/denom
    return out


def choose_pool_setting(pool_auc):
    candidates = [i for i, s in enumerate(SETTINGS) if s[2] == 'natural']
    default = SETTINGS.index(DEFAULT)
    return min(candidates, key=lambda i: (-pool_auc[i], i != default, SETTINGS[i][0], SETTINGS[i][1]))


def metric_values(auc, selected):
    """Pure transformations reused for point and paired bootstrap estimates."""
    auc = np.asarray(auc)
    vals, names = [], []
    default = SETTINGS.index(DEFAULT)
    for i, (layer, gain, arm) in enumerate(SETTINGS):
        title = f'L{layer}/g{gain:g}/{arm}'
        vals.append(auc[..., i]); names.append(f'auroc/{title}')
        vals.append(auc[..., i]-auc[..., default]); names.append(f'delta_default/{title}')
        if arm == 'natural':
            vals.append(auc[..., i]-auc[..., i+1]); names.append(f'delta_shuffled/{title}')
    natural = np.stack([auc[..., i] for i, s in enumerate(SETTINGS) if s[2] == 'natural'], axis=-1)
    grid = natural.reshape(natural.shape[:-1]+(len(LAYERS), len(GAINS)))
    gain_range = np.ptp(grid, axis=-1).max(axis=-1)
    layer_range = np.ptp(grid, axis=-2).max(axis=-1)
    extra = {'gain_range': gain_range, 'layer_range': layer_range,
             'gain_range_minus_005': gain_range-.05, 'layer_range_minus_005': layer_range-.05,
             'default_gain_slice_range': np.ptp(grid[..., LAYERS.index(44), :], axis=-1),
             'default_layer_slice_range': np.ptp(grid[..., :, GAINS.index(1.)], axis=-1),
             'nuisance_robust_share': ((gain_range <= .05) & (layer_range <= .05)).astype(float),
             'selected_test_auc': auc[..., selected], 'default_test_auc': auc[..., default],
             'selected_minus_default': auc[..., selected]-auc[..., default],
             'selected_minus_shuffled': auc[..., selected]-auc[..., selected+1]}
    for k, v in extra.items():
        names.append(k); vals.append(v)
    return np.stack(vals, axis=-1), names


def interval(point, item_draws, corpus_draws):
    if not np.isfinite(item_draws).all() or not np.isfinite(corpus_draws).all():
        raise ValueError('Nonfinite bootstrap draw; cannot silently omit a denominator')
    a = np.quantile(item_draws, [.025, .975], axis=0)
    b = np.quantile(corpus_draws, [.025, .975], axis=0)
    return {'estimate': float(point), 'item_ci95': [float(a[0]), float(a[1])],
            'corpus_ci95': [float(b[0]), float(b[1])],
            'quoted_ci95': [float(min(a[0], b[0])), float(max(a[1], b[1]))]}


def analyze_rows(rows, manifest, n_boot=2000):
    assert_coverage(rows, manifest)
    rowmap = {r['key']: r for r in rows}
    points, item_draws, corpus_draws, selection, names = [], [], [], [], None
    rng = np.random.default_rng(SEED+5)
    by_corpus = defaultdict(list)
    for f in manifest['facts']:
        by_corpus[f['corpus']].append(f)
    doc_weights = {}
    for corpus, facts in by_corpus.items():
        docs = sorted({it['text_hash'] for f in facts for it in f['items'] if it['split'] == 'test'})
        mapping = {d: k for k, d in enumerate(docs)}
        weights = rng.multinomial(len(docs), np.full(len(docs), 1/len(docs)), size=n_boot)
        doc_weights[corpus] = mapping, weights
    fact_reports = []
    for fact in manifest['facts']:
        ds = fact['dataset']
        data = {}
        for split in ('pool', 'test'):
            its = [it for it in fact['items'] if it['split'] == split]
            y = np.array([it['label'] for it in its])
            s = np.array([[rowmap[row_key(ds, it['item_id'], *setting)]['score'] for setting in SETTINGS] for it in its])
            data[split] = (its, y, s)
        pool_items, pool_y, pool_s = data['pool']
        chosen = choose_pool_setting(weighted_auc(pool_y, pool_s, np.ones(len(pool_y)))[0])
        its, y, s = data['test']
        item_w = rng.multinomial(len(y), np.full(len(y), 1/len(y)), size=n_boot)
        mapping, weights = doc_weights[fact['corpus']]
        cluster_w = weights[:, [mapping[it['text_hash']] for it in its]]
        a0 = weighted_auc(y, s, np.ones(len(y)))[0]
        ai = weighted_auc(y, s, item_w)
        ac = weighted_auc(y, s, cluster_w)
        pt, names = metric_values(a0, chosen)
        di, _ = metric_values(ai, chosen)
        dc, _ = metric_values(ac, chosen)
        points.append(pt); item_draws.append(di); corpus_draws.append(dc)
        report = {'dataset': ds, 'tag': fact['tag'], 'corpus': fact['corpus'],
                  'selected_setting': list(SETTINGS[chosen]), 'selection_split': 'pool',
                  'pool_selected_auc': float(weighted_auc(pool_y, pool_s, np.ones(len(pool_y)))[0, chosen]),
                  'corpus_ci_limitation': 'One fact belongs to one corpus; this interval resamples shared documents, not independent corpora.',
                  'metrics': {name: interval(pt[k], di[:, k], dc[:, k]) for k, name in enumerate(names)}}
        robust = bool(pt[names.index('nuisance_robust_share')])
        upper = max(report['metrics'][k]['quoted_ci95'][1] for k in ('gain_range', 'layer_range'))
        report['nuisance_robust_point'] = robust
        report['nuisance_robust_confirmed'] = robust and upper <= .05
        report['nuisance_robust_uncertain'] = robust and not report['nuisance_robust_confirmed']
        fact_reports.append(report)
        selection.append(chosen)
    points, item_draws, corpus_draws = np.array(points), np.stack(item_draws, axis=1), np.stack(corpus_draws, axis=1)
    pop_reports = []
    for tag in ['all']+sorted({f['tag'] for f in manifest['facts']}):
        fs = [i for i, f in enumerate(manifest['facts']) if tag == 'all' or f['tag'] == tag]
        fsub = [manifest['facts'][i] for i in fs]
        corpus_ids = sorted({f['corpus'] for f in fsub})
        groups = [[fs[j] for j, f in enumerate(fsub) if f['corpus'] == corpus] for corpus in corpus_ids]
        iid_samples = rng.choice(fs, size=(n_boot, len(fs)), replace=True)
        di = item_draws[np.arange(n_boot)[:, None], iid_samples].mean(axis=1)
        dc = np.empty_like(di)
        for b in range(n_boot):
            drawn = []
            for ci in rng.integers(len(groups), size=len(groups)):
                drawn.extend(rng.choice(groups[ci], size=len(groups[ci]), replace=True))
            dc[b] = corpus_draws[b, drawn].mean(axis=0)
        pt = points[fs].mean(axis=0)
        pop_reports.append({'tag': tag, 'n_facts': len(fs), 'n_corpora': len(corpus_ids),
                            'metrics': {name: interval(pt[k], di[:, k], dc[:, k]) for k, name in enumerate(names)}})
    return {'facts': fact_reports, 'population': pop_reports, 'n_boot': n_boot,
            'ci': 'Envelope of paired fact-item and corpus-fact-shared-document intervals; pool selection held fixed.'}


def load_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def mock_smoke(cache, results, meta):
    """Small fixture, all setting/arm/split cells, no real outcome rows or model."""
    from types import SimpleNamespace
    root = cache/'mock'
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    facts, items_by_id = [], {}
    for k in range(2):
        ds = f'mock{k}'
        its = []
        for split in ('pool', 'test'):
            for j in range(20):
                iid = f'{ds}-{split}-{j:03}'
                it = {'item_id': iid, 'dataset': ds, 'tag': 'MOCK', 'split': split, 'label': j%2,
                      'text_hash': f'doc{k}-{j}', 'state_row': len(its)}
                its.append(it)
                items_by_id[iid] = {**it, 'primary': {'candidates': ['yes', 'no']}}
        for split in ('pool', 'test'):
            donors = derangement([it['item_id'] for it in its if it['split'] == split], ds+split)
            lookup = {it['item_id']: it['state_row'] for it in its}
            for it in its:
                if it['split'] == split:
                    it['donor_item_id'] = donors[it['item_id']]
                    it['donor_state_row'] = lookup[it['donor_item_id']]
        (root/ds).mkdir(exist_ok=True)
        for layer in LAYERS:
            H = rng.normal(size=(len(its), 8)).astype(np.float32)
            H[:, 0] += np.array([it['label'] for it in its])*2
            np.save(root/ds/f'chat_L{layer}.npy', H)
        facts.append({'dataset': ds, 'tag': 'MOCK', 'corpus': ds, 'items': its})
    manifest = {'facts': facts, 'n_facts': 2, 'n_test': 20, 'n_pool': 20, 'base_alpha': 16000.,
                'expected_rows': 2*40*len(SETTINGS), 'errors': []}
    def scorer(reader, H, items, layer, batch):
        return [{'lo': float(v[0]*reader.alpha/16000), 'lp_A': float(v[0]), 'lp_B': 0.} for v in H]
    target = root/'scores.jsonl'
    if target.exists():
        target.unlink()  # Only a declared synthetic fixture may be replaced.
    reader = SimpleNamespace(alpha=777.)
    rows, timing = collect_scores(manifest, items_by_id, reader, scorer, {**meta, 'mock': True}, target, states_dir=root)
    assert reader.alpha == 777.
    summary = analyze_rows(rows, manifest, n_boot=100)
    write_json(results/'mock_validation.json', {**meta, 'mock': True, 'live_gate': False,
               'coverage_rows': len(rows), 'expected_rows': manifest['expected_rows'],
               'all_settings_arms_splits': True, 'alpha_restored': True, 'analysis_completed': bool(summary['population'])})
    print(f'MOCK SMOKE PASSED: {len(rows)} synthetic rows; not a live certificate')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase', choices=('preflight', 'smoke', 'run', 'analyze'), required=True)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true')
    mode.add_argument('--mock', action='store_true')
    p.add_argument('--pod', required=True)
    p.add_argument('--deadline-epoch', type=float)
    p.add_argument('--batch', type=int, default=32)
    p.add_argument('--n-boot', type=int, default=2000)
    args = p.parse_args(argv)
    if args.batch < 2:
        p.error('--batch counts candidate sequences and must be >=2')
    CACHE.mkdir(parents=True, exist_ok=True); RESULTS.mkdir(parents=True, exist_ok=True)
    meta = metadata(args.pod)
    if args.phase == 'smoke' and args.mock:
        mock_smoke(CACHE, RESULTS, meta)
        return 0
    if args.mock:
        p.error('--mock only supports phase smoke')
    items = json.loads(BANK.read_text())['items']
    current = make_manifest(items)
    write_json(RESULTS/'preflight.json', {**meta, 'errors': current['errors'], 'n_facts': len(current['facts']),
                                       'expected_rows': current['expected_rows'], 'expected_candidate_sequences': current['expected_rows']*2,
                                       'manifest_sha': digest(current)})
    freeze_manifest(current, RESULTS/'manifest.json')
    if args.phase == 'preflight':
        print(f"PREFLIGHT PASSED: {len(current['facts'])} facts; {current['expected_rows']} rows expected; no GPU loaded")
        return 0
    if args.phase == 'analyze':
        if args.n_boot < 2000:
            p.error('Registered analysis requires >=2000 bootstrap draws')
        rows = load_rows(CACHE/'scores.jsonl')
        if any(r.get('mock') for r in rows):
            raise ValueError('Refuse synthetic outcomes as results')
        if any(r.get('manifest_sha') != digest(current) for r in rows):
            raise ValueError('Manifest differs from scored rows')
        result = analyze_rows(rows, current, args.n_boot)
        write_json(RESULTS/'analysis.json', {**meta, **result})
        lines = ['# R5 insertion gain/site results', '', result['ci'], '', '| Tag | Facts | Selected−default AUROC, 95% CI | Robust share, 95% CI |', '|---|---:|---|---|']
        for group in result['population']:
            d = group['metrics']['selected_minus_default']; r = group['metrics']['nuisance_robust_share']
            lines.append(f"| {group['tag']} | {group['n_facts']} | {d['estimate']:.3f} {d['quoted_ci95']} | {r['estimate']:.3f} {r['quoted_ci95']} |")
        (RESULTS/'REPORT.md').write_text('\n'.join(lines)+'\n')
        return 0
    if args.phase == 'smoke' and not args.live:
        p.error('Smoke requires explicit --mock or --live')
    live_authorized(args.pod, args.deadline_epoch)
    certificate = None
    if args.phase == 'run':
        certificate = json.loads((CACHE/'live_smoke.json').read_text())
        gate = throughput_gate(certificate, current, meta, args.deadline_epoch, args.batch)
        write_json(RESULTS/'throughput_gate.json', {**meta, **gate})
    from projects.g_agreement.core import model as M, readers as R
    from projects.g_agreement.r_bench import collect as RC
    target = M.load_target()
    reader = R.OLensReader().bind(target)
    if certificate is not None:
        throughput_gate(certificate, current, meta, args.deadline_epoch, args.batch)
    rows, timing = collect_scores(current, {it['item_id']: it for it in items}, reader, RC.score_items,
                                 {**meta, 'mock': False}, CACHE/('live_smoke_scores.jsonl' if args.phase == 'smoke' else 'scores.jsonl'),
                                 smoke=args.phase == 'smoke', batch=args.batch, deadline_epoch=args.deadline_epoch)
    if args.phase == 'smoke':
        cert = {**meta, 'mock': False, 'live': True, 'manifest_sha': digest(current), 'coverage_rows': len(rows),
                'batch': args.batch, 'deadline_epoch': args.deadline_epoch, 'timing': timing}
        write_json(CACHE/'live_smoke.json', cert)
        gate = throughput_gate(cert, current, meta, args.deadline_epoch, args.batch)
        write_json(RESULTS/'throughput_gate.json', {**meta, **gate})
    print(f"LIVE {args.phase.upper()} PASSED: {len(rows)} rows")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
