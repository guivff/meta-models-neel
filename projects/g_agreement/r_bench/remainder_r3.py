"""Remainder R3: CPU-only cross-reader aggregation; BRIEF_R §21.

No model or API imports. All new artifacts are scoped to remainder/r3.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from projects.g_agreement.r_bench import analyze as A
from projects.g_agreement.r_bench import interim as I
from projects.g_agreement.r_bench.th2_preflight import READERS, LAYERS, split_bank, _file_sha

SEED = 20261023
BOOT_SEED = 20261024
METHODS = ('majority', 'best_single', 'confidence_weighted', 'prevalence')
REFERENCES = ('label', 'target_probe', 'pair_conditional_model')
VARIANTS = ('native', 'calibrated')

def metadata(root):
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    return {'pod': 'local-cpu-remainder-r3', 'git_sha': sha,
            'code_sha': _file_sha(Path(__file__)), 'timestamp': datetime.now(timezone.utc).isoformat()}

def stamp(frame, meta):
    frame = frame.copy()
    for key, value in meta.items(): frame[key] = value
    return frame

def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+'\n')

def calibrator(x, y):
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1., solver='lbfgs', max_iter=1000, random_state=SEED))
    return model.fit(np.asarray(x).reshape(-1, 1), y)

def probability(model, x):
    return model.predict_proba(np.asarray(x).reshape(-1, 1))[:, 1]

def aggregate(pool_x, pool_y, test_x, sided):
    """Fit only on pool, select by OOF/ native pool accuracy, never accept test labels."""
    pool_x, test_x = np.asarray(pool_x), np.asarray(test_x)
    pool_y = np.asarray(pool_y, dtype=int)
    assert pool_x.shape[1] == test_x.shape[1] == len(READERS)
    assert len(pool_y) >= 24 and np.bincount(pool_y, minlength=2).min() >= 8
    oof = np.zeros_like(pool_x, dtype=float)
    folds = list(StratifiedKFold(4, shuffle=True, random_state=SEED).split(pool_x, pool_y))
    test_p = np.empty_like(test_x, dtype=float)
    fit_rows = []
    for j, reader in enumerate(READERS):
        for train, valid in folds:
            model = calibrator(pool_x[train, j], pool_y[train])
            oof[valid, j] = probability(model, pool_x[valid, j])
        model = calibrator(pool_x[:, j], pool_y)
        test_p[:, j] = probability(model, test_x[:, j])
        fit_rows.append({'reader': reader, 'coefficient': float(model[-1].coef_[0, 0]),
                         'intercept': float(model[-1].intercept_[0]),
                         'score_mean': float(model[0].mean_[0]), 'score_scale': float(model[0].scale_[0])})
    thresholds = np.zeros(len(READERS)) if sided == 'two' else np.median(pool_x, axis=0)
    native_pool = pool_x > thresholds
    native_test = test_x > thresholds
    prevalence = float(pool_y.mean())
    output = {}
    for variant in VARIANTS:
        votes = native_test if variant == 'native' else test_p > .5
        accuracy = ((native_pool if variant == 'native' else oof > .5) == pool_y[:, None]).mean(axis=0)
        best = int(np.argmax(accuracy))
        reliability = np.maximum(0, 2 * accuracy - 1)
        if reliability.sum() == 0: reliability[:] = 1
        majority = votes.mean(axis=1)
        if variant == 'native':
            support = np.where(votes, test_p, 1 - test_p)
            weight = reliability * np.maximum(0, 2 * support - 1)
            total = weight.sum(axis=1)
            weighted = np.divide((weight * votes).sum(axis=1), total, out=majority.copy(), where=total > 0)
            confidence = np.maximum(.5, support[:, best])
            best_p = np.where(votes[:, best], confidence, 1 - confidence)
        else:
            weighted = test_p @ reliability / reliability.sum()
            best_p = test_p[:, best]
        output[variant] = {
            'majority': (majority, majority > .5),
            'best_single': (best_p, votes[:, best]),
            'confidence_weighted': (weighted, weighted > .5),
            'prevalence': (np.full(len(test_x), prevalence), np.full(len(test_x), prevalence > .5)),
        }
        for j, row in enumerate(fit_rows):
            row[f'{variant}_pool_accuracy'] = float(accuracy[j])
            row[f'{variant}_reliability'] = float(reliability[j])
            row[f'{variant}_selected'] = j == best
            row['native_threshold'] = float(thresholds[j])
    return output, fit_rows

def load_rows(root, out, cache, meta):
    bank_path = root / 'projects/g_agreement/dataset/items_r.json'
    bank_hash = _file_sha(bank_path)
    frozen = json.loads((root / 'projects/g_agreement/manifest/frozen_config_r.json').read_text())
    assert frozen['items_sha256']['items_r.json'] == bank_hash
    bank = pd.DataFrame(json.loads(bank_path.read_text())['items'])
    bank['sided'] = bank.primary.map(lambda p: p['sided'])
    bank, groups = split_bank(bank)
    assert not bank.item_id.duplicated().any()
    by_id = bank.set_index('item_id').to_dict('index')
    datasets = set(bank.dataset)
    source_files = A.shard_files(root / 'cache/g_agreement/r', 'reader_lo')
    rows = {}; source = []; raw_repeats = 0
    for path in source_files:
        start = path.stat(); digest = hashlib.sha256(); total = selected = 0
        is_d = path.name.split('.')[-2] == 'D'
        with path.open('rb') as stream:
            for line in stream:
                digest.update(line)
                if not line.strip(): continue
                row = json.loads(line)  # no incomplete-tail tolerance for final evidence
                total += 1
                if is_d or row.get('dataset') not in datasets or row.get('pod') in A.EXCLUDED_PODS: continue
                if row.get('reader') not in READERS: continue
                if row.get('layer') != LAYERS[row['reader']] or row.get('render') != 'chat': continue
                if row.get('condition') not in ('natural', 'pool_eval') or row.get('position', 'last') not in ('last', None): continue
                assert row.get('pod') in A.ALLOWED_PODS, f'Invalid pod: {path}:{row.get("key")}'
                assert str(row.get('git_sha'))[:7] == A.FROZEN_GIT_SHA
                assert row.get('items_sha256') == bank_hash and row.get('items_file') == 'items_r.json'
                item = by_id[row['item_id']]
                assert row['dataset'] == item['dataset'] and row['label'] == item['label']
                assert row.get('state_item_id') == row['item_id']
                assert ('pool' if row['split'] == 'pool_eval' else row['split']) == item['split']
                pair = item['primary']['candidates']
                if row['reader'] == 'jlens':
                    short = item['primary'].get('jlens') or [None, None]
                    pair = [short[i] or pair[i] for i in range(2)]
                assert [row['cand_A'], row['cand_B']] == pair
                score = row['lo'] if item['sided'] == 'two' else row['lp_A']
                if row.get('unscorable') or score is None or not np.isfinite(score): continue
                selected += 1
                key = row['key']
                if key in rows: raw_repeats += 1
                rows[key] = {'dataset': row['dataset'], 'item_id': row['item_id'], 'reader': row['reader'],
                             'score': float(score), 'source_pod': row['pod'], 'source_git_sha': row['git_sha']}
        after = path.stat()
        assert (start.st_size, start.st_mtime_ns) == (after.st_size, after.st_mtime_ns), f'Input changed: {path}'
        source.append({'path': str(path.relative_to(root)), 'sha256': digest.hexdigest(), 'bytes': start.st_size,
                       'rows': total, 'selected': selected, **meta})
        print(f'R3 inventory {path.name}: {total:,} rows; {selected:,} selected', flush=True)
    frame = pd.DataFrame(rows.values())
    assert not frame.duplicated(['dataset', 'item_id', 'reader']).any()
    wide = frame.pivot(index=['dataset', 'item_id'], columns='reader', values='score').reindex(columns=READERS).reset_index()
    wide = wide.merge(bank.drop(columns=['primary']), on=['dataset', 'item_id'], validate='one_to_one')
    all_test_hashes = set(bank.loc[bank.split.eq('test'), 'text_hash'])
    wide['pool_clean'] = wide.split.eq('pool') & ~wide.text_hash.isin(all_test_hashes)
    wide['complete'] = wide[list(READERS)].notna().all(axis=1)
    coverage = []; kept = []
    for dataset, group in wide.groupby('dataset', sort=True):
        pool = group[group.pool_clean & group.complete]
        test = group[group.split.eq('test') & group.complete]
        bank_test = bank[bank.dataset.eq(dataset) & bank.split.eq('test')]
        y = np.bincount(pool.label.astype(int), minlength=2)
        eligible = dataset not in I.LABEL_DEFECT and len(test) == len(bank_test) and len(pool) >= 24 and y.min() >= 8
        coverage.append({'dataset': dataset, 'bank_test': len(bank_test), 'complete_test': len(test), 'clean_pool': len(pool),
                         'pool0': int(y[0]), 'pool1': int(y[1]), 'label_defect': dataset in I.LABEL_DEFECT, 'eligible': eligible})
        if eligible: kept.append(pd.concat([pool, test]))
    assert kept, 'No eligible datasets'
    # Reuse audited target probe hard choices. This is the 256-item pool fit, not probe(512).
    reference_path = root / 'results/g_agreement/r/i2/th2_f1_rows.csv.gz'
    reference = pd.read_csv(reference_path)
    assert not reference.duplicated(['dataset', 'item_id']).any()
    reference['target_probe'] = np.where(reference.e_probe.notna(), np.logical_xor(reference.label, reference.e_probe), np.nan)
    reference['pair_conditional_model'] = np.where(reference.e_prompt_only.notna(), np.logical_xor(reference.label, reference.e_prompt_only), np.nan)
    reference = reference[['dataset', 'item_id', 'label', 'target_probe', 'pair_conditional_model']].rename(columns={'label': 'reference_label'})
    selected = pd.concat(kept, ignore_index=True).merge(reference, on=['dataset', 'item_id'], how='left', validate='one_to_one')
    assert (selected.loc[selected.reference_label.notna(), 'label'] == selected.loc[selected.reference_label.notna(), 'reference_label']).all()
    stamp(pd.DataFrame(coverage), meta).to_csv(out / 'coverage.csv', index=False)
    stamp(selected.drop(columns=['prompt_text'], errors='ignore'), meta).to_csv(cache / 'selected_scores.csv.gz', index=False)
    source.append({'path': str(reference_path.relative_to(root)), 'sha256': _file_sha(reference_path), **meta})
    write_json(out / 'sources.json', {'bank_sha256': bank_hash, 'sources': source, 'raw_key_repeats': raw_repeats,
                                     'LABEL_DEFECT': sorted(I.LABEL_DEFECT), 'groups': groups, **meta})
    return selected

def predictions(selected, meta):
    output = []; fits = []
    for dataset, group in selected.groupby('dataset', sort=True):
        pool = group[group.split.eq('pool')].sort_values('item_id')
        test = group[group.split.eq('test')].sort_values('item_id')
        arms, fit = aggregate(pool[list(READERS)].to_numpy(), pool.label.to_numpy(), test[list(READERS)].to_numpy(), pool.sided.iloc[0])
        keep = ['dataset', 'item_id', 'tag', 'corpus_group', 'text_hash', *REFERENCES]
        rows = test[keep].copy()
        for variant, methods in arms.items():
            for method, (p, vote) in methods.items():
                rows[f'{variant}_{method}_p'] = p
                rows[f'{variant}_{method}_vote'] = vote.astype(int)
        output.append(rows)
        training_hash = hashlib.sha256('|'.join(pool.item_id).encode()).hexdigest()
        fits.extend({'dataset': dataset, 'pool_n': len(pool), 'pool_ids_sha256': training_hash, **row} for row in fit)
    return stamp(pd.concat(output, ignore_index=True), meta), stamp(pd.DataFrame(fits), meta)

def ece(y, p, weight=None):
    y, p = np.asarray(y), np.asarray(p)
    w = np.ones(len(y)) if weight is None else np.asarray(weight)
    bins = np.minimum((p * 10).astype(int), 9)
    signed = np.bincount(bins, weights=w * (p - y), minlength=10)
    return float(np.abs(signed).sum() / w.sum())

def statistic_matrix(frame):
    """Linear accuracy and signed calibration-bin sums permit paired bootstrap."""
    columns = []; schema = []
    for reference in REFERENCES:
        y = frame[reference].to_numpy(float)
        valid = np.isfinite(y)
        for variant in VARIANTS:
            for method in METHODS:
                p = frame[f'{variant}_{method}_p'].to_numpy()
                vote = frame[f'{variant}_{method}_vote'].to_numpy()
                parts = [valid.astype(float), (valid & (vote == y)).astype(float)]
                bins = np.minimum((p * 10).astype(int), 9)
                for b in range(10): parts.append(np.where(valid & (bins == b), p - y, 0))
                columns.extend(parts); schema.append((reference, variant, method))
    return np.asarray(columns, dtype=float).T, schema

def unpack(value, schema):
    value = value.reshape(len(schema), 12)
    denominator = value[:, 0]
    accuracy = np.divide(value[:, 1], denominator, out=np.full(len(schema), np.nan), where=denominator > 0)
    calibration = np.divide(np.abs(value[:, 2:]).sum(axis=1), denominator, out=np.full(len(schema), np.nan), where=denominator > 0)
    return np.stack([accuracy, calibration], axis=1)

def bootstrap_group(frame, n_boot, seed):
    """Equal-fact estimates; corpus draws share document multiplicities across facts."""
    frame = frame.reset_index(drop=True)
    matrix, schema = statistic_matrix(frame)
    fact_ids = sorted(frame.dataset.unique())
    fact_rows = [np.flatnonzero(frame.dataset.eq(ds)) for ds in fact_ids]
    point_weights = np.zeros(len(frame))
    for ix in fact_rows: point_weights[ix] = 1 / len(ix) / len(fact_rows)
    point = unpack(point_weights @ matrix, schema)
    corpus_names = sorted(frame.corpus_group.unique())
    corpus_facts = [[j for j, ds in enumerate(fact_ids) if frame.iloc[fact_rows[j][0]].corpus_group == c] for c in corpus_names]
    corpus_docs = []
    for fs in corpus_facts:
        ix = np.concatenate([fact_rows[j] for j in fs])
        _, inverse = np.unique(frame.loc[ix, 'text_hash'], return_inverse=True)
        row_doc = np.full(len(frame), -1, dtype=int); row_doc[ix] = inverse
        corpus_docs.append((row_doc, int(inverse.max()) + 1))
    samples = {}
    for scheme in ('fact_item', 'corpus_fact_document'):
        rng = np.random.default_rng(seed + int(scheme.startswith('corpus')))
        values = np.empty((n_boot, len(schema), 2))
        for b in range(n_boot):
            weight = np.zeros(len(frame))
            if scheme == 'fact_item':
                for j in rng.integers(len(fact_rows), size=len(fact_rows)):
                    ix = fact_rows[j]
                    counts = rng.multinomial(len(ix), np.full(len(ix), 1 / len(ix)))
                    weight[ix] += counts / len(ix)
            else:
                for c in rng.integers(len(corpus_names), size=len(corpus_names)):
                    fs = corpus_facts[c]; row_doc, n_docs = corpus_docs[c]
                    counts = rng.multinomial(n_docs, np.full(n_docs, 1 / n_docs))
                    for j in rng.choice(fs, size=len(fs), replace=True):
                        ix = fact_rows[j]; ww = counts[row_doc[ix]].astype(float)
                        # Extremely small facts can get no document; preserve explicit failed draw.
                        if ww.sum() == 0: ww[:] = 1
                        weight[ix] += ww / ww.sum()
            weight /= weight.sum()
            values[b] = unpack(weight @ matrix, schema)
        samples[scheme] = values
    return point, samples, schema

def summarize(frame, n_boot, meta):
    output = []
    strata = [('ALL', frame)] + [(str(tag), group) for tag, group in frame.groupby('tag', sort=True)]
    for group_number, (tag, group) in enumerate(strata):
        print(f'R3 bootstrap {tag}: {len(group):,} items / {group.dataset.nunique()} facts, {n_boot} draws per scheme', flush=True)
        point, draws, schema = bootstrap_group(group, n_boot, BOOT_SEED + group_number * 100)
        lookup = {entry: j for j, entry in enumerate(schema)}
        for j, (reference, variant, method) in enumerate(schema):
            valid = group[reference].notna()
            for metric_index, metric in enumerate(('accuracy', 'ece')):
                for control in ('absolute', 'best_single', 'prevalence'):
                    k = lookup[(reference, variant, control)] if control != 'absolute' else None
                    value = point[j, metric_index] - (point[k, metric_index] if k is not None else 0)
                    row = {'tag': tag, 'variant': variant, 'reference': reference, 'method': method, 'metric': metric,
                           'control': control, 'value': float(value), 'n_items': int(valid.sum()),
                           'n_facts': int(group.loc[valid, 'dataset'].nunique()), 'n_corpora': int(group.loc[valid, 'corpus_group'].nunique())}
                    intervals = []
                    for scheme, values in draws.items():
                        distribution = values[:, j, metric_index] - (values[:, k, metric_index] if k is not None else 0)
                        interval = np.nanquantile(distribution, [.025, .975])
                        row[f'{scheme}_lo'], row[f'{scheme}_hi'] = map(float, interval)
                        row[f'{scheme}_valid'] = int(np.isfinite(distribution).sum())
                        intervals.append(interval)
                    row['ci_lo'] = float(min(x[0] for x in intervals)); row['ci_hi'] = float(max(x[1] for x in intervals))
                    output.append(row)
    return stamp(pd.DataFrame(output), meta)

def assert_coverage(pred, metrics=None):
    for variant in VARIANTS:
        for method in METHODS:
            name = f'{variant}_{method}_p'
            if name not in pred or len(pred) == 0 or not np.isfinite(pred[name]).all():
                raise AssertionError(f'SMOKE FAILED: missing {variant}/{method}')
            assert pred[name].between(0, 1).all()
            for reference in REFERENCES:
                if reference not in pred or not pred[reference].notna().any(): raise AssertionError(f'SMOKE FAILED: missing {variant}/{method}/{reference}')
    if metrics is not None:
        for variant in VARIANTS:
            for method in METHODS:
                for reference in REFERENCES:
                    for metric in ('accuracy', 'ece'):
                        q = metrics[(metrics.variant == variant) & (metrics.method == method) & (metrics.reference == reference) & (metrics.metric == metric)]
                        assert len(q), f'SMOKE FAILED: missing {variant}/{method}/{reference}/{metric}'
                        assert np.isfinite(q[['value', 'ci_lo', 'ci_hi']]).all().all()
    print('SMOKE PASSED: every 2 variants × 4 aggregate/control arms × 3 available references has finite rows; true greedy explicitly unavailable', flush=True)

def smoke(meta):
    rng = np.random.default_rng(SEED)
    frames = []
    for i in range(3):
        pool_y = np.tile([0, 1], 16); y = np.tile([0, 1], 10)
        arms, _ = aggregate(pool_y[:, None] + rng.normal(0, .4, (32, 4)), pool_y,
                            y[:, None] + rng.normal(0, .4, (20, 4)), 'one' if i % 2 else 'two')
        frame = pd.DataFrame({'dataset': f'd{i}', 'item_id': [f'{i}:{j}' for j in range(20)], 'tag': 'MOCK',
                              'corpus_group': f'c{i}', 'text_hash': [f'{i}-{j}' for j in range(20)],
                              'label': y, 'target_probe': y, 'pair_conditional_model': y})
        for variant in VARIANTS:
            for method, (p, vote) in arms[variant].items():
                frame[f'{variant}_{method}_p'] = p; frame[f'{variant}_{method}_vote'] = vote.astype(int)
        frames.append(frame)
    pred = pd.concat(frames, ignore_index=True)
    metrics = summarize(pred, 10, meta)
    assert_coverage(pred, metrics)
    return {'status': 'PASSED', 'variants': list(VARIANTS), 'methods': list(METHODS), 'references': list(REFERENCES), **meta}

def render_report(metrics, pred, out, meta, seconds):
    rows = metrics[metrics.tag.eq('ALL') & metrics.variant.eq('native')]
    def get(reference, method, metric, control='absolute'):
        return rows[(rows.reference == reference) & (rows.method == method) & (rows.metric == metric) & (rows.control == control)].iloc[0]
    def interval(row): return f"{row.value:.4f} [{row.ci_lo:.4f}, {row.ci_hi:.4f}]"
    lines = ['# R3 — cross-reader consensus', '', f'Completed {meta["timestamp"]}; CPU only, 0 pod/judge spend. BRIEF_R §21.', '',
             f'{len(pred):,} held-out test items; {pred.dataset.nunique()} nondefect R-A facts; {pred.corpus_group.nunique()} corpus groups. Native votes are primary. Four readers: J-lens42, Oracle44, NLA42, skip_a42.', '',
             'Intervals are the envelope of 1,000 fact→item and corpus→fact→shared-document paired bootstraps, equal fact weighting. Pool calibrations and reader selection are held fixed. Each effect is method minus control; negative ECE differences improve calibration.', '',
             '| Reference | Method | Accuracy [95% CI] | Δ accuracy vs best [95% CI] | ECE [95% CI] | Δ ECE vs best [95% CI] |',
             '|---|---|---|---|---|---|']
    for reference in REFERENCES:
        for method in METHODS:
            lines.append(f'| {reference} | {method} | {interval(get(reference, method, "accuracy"))} | {interval(get(reference, method, "accuracy", "best_single"))} | {interval(get(reference, method, "ece"))} | {interval(get(reference, method, "ece", "best_single"))} |')
    lines.extend(['', '**Frozen decision rule:** label accuracy gain ≥ .02, lower 95% bound >0, ECE deterioration ≤ .02.'])
    for method in ('majority', 'confidence_weighted'):
        a = get('label', method, 'accuracy', 'best_single'); e = get('label', method, 'ece', 'best_single')
        verdict = 'USEFUL' if a.value >= .02 and a.ci_lo > 0 and e.value <= .02 else 'NOT DEMONSTRATED'
        lines.append(f'- {method}: **{verdict}** (Δ accuracy {interval(a)}; Δ ECE {interval(e)}).')
    lines.extend(['', '**Actual greedy target comparison: NOT AVAILABLE.** R-A prompt-only `model_says_pos` is the sign of teacher-forced pair-conditional LO; it is not a saved unconstrained full-vocabulary greedy continuation. Its separately named comparator above cannot answer agreement with the model’s actual greedy text. Existing `model_labels.RB.jsonl` belongs to ReaderBench and does not cover this R-A population.', '',
                  '**Probe reference:** reused TH-2-F1 logistic state probe at L42, fitted on 256 globally document-clean pool items; this is not probe(512). Agreement with a probe is a comparator, not truth validation. Every reference is evaluated on its own declared available coverage.', '',
                  '**Calibration:** majority probability is fraction of positive native votes. Weighted probability is a positive native vote fraction weighted by pool reliability and calibrated support for each vote, with majority fallback. Best-single confidence is a pool-calibrated native-decision probability clipped at .5 when calibration disagrees; accuracy retains the native decision even at confidence .5. ECE is ten fixed equal-width bins. The calibrated-vote sensitivity, every per-tag result, and both bootstrap intervals are in `metrics.csv`. Pool-derived best-single is a per-fact selection policy, not an oracle chosen on test accuracy.', '',
                  '**TH-2 caveat:** shared difficulty already predicts four-reader failure tails on these facts. Reader agreement, a majority gain, or good ECE does not establish independent evidence or a shared neural mechanism. These are retrospective natural-state results. No conclusion about sample recurrence is possible before the pending R6 generation and separately approved truth/support judging.', '',
                  '**Sampling prepared, not launched:** R6 `--profile r3-sampling` uses the same 20 frozen states per C1–C4, 8 samples per state/reader/site, temperature .7, top_p .9, top_k 64. Kenney recurrence is semantic support in 8 reports for first-sample atomic claims; the lexical proxy in `for_michael.md` is not substituted. Judge/rubric is preregistered in R6; evaluate support thresholds 1/8…8/8 and preserve confident wrong claims. Estimate 0.33 pod-h (site count and output length may increase this); launch requires per-experiment go, booking, guards, coverage smoke, and Mac pull before stop.', '',
                  f'CPU wall time: {seconds:.1f}s. Provenance: pod `{meta["pod"]}`, git `{meta["git_sha"]}`, code `{meta["code_sha"]}`. Inputs and provenance audits: `sources.json`; coverage/exclusions: `coverage.csv`; pool fits: `pool_fits.csv`; full predictions in experiment cache. No shared input artifacts were changed.', '',
                  '**Deviations:** The pre-compute native-primary clarification is appended to §21 and PLAN. No rule or threshold changed after seeing R3 results. Other-bank multi-reader panels are outside this frozen R-A analysis rather than pooled across incompatible coverage. Genuine greedy is missing; collecting it would require separately approved inference.'])
    (out / 'REPORT.md').write_text('\n'.join(lines)+'\n')

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--stage', choices=['smoke', 'run'], default='smoke')
    parser.add_argument('--root', type=Path, default=Path.cwd()); parser.add_argument('--n-boot', type=int, default=1000)
    args = parser.parse_args(); root = args.root.resolve(); started = time.monotonic(); meta = metadata(root)
    out = root / 'results/g_agreement/r/remainder/r3'; cache = root / 'cache/g_agreement/r/remainder/r3'
    out.mkdir(parents=True, exist_ok=True); cache.mkdir(parents=True, exist_ok=True)
    if args.stage == 'smoke':
        write_json(out / 'smoke.json', smoke(meta)); return
    assert args.n_boot >= 1000, 'Full run requires the registered 1000 bootstrap draws'
    gate = json.loads((out / 'smoke.json').read_text())
    assert gate['status'] == 'PASSED' and gate['code_sha'] == meta['code_sha'], 'Run current-code smoke first'
    selected = load_rows(root, out, cache, meta)
    pred, fits = predictions(selected, meta)
    assert_coverage(pred)
    pred.to_csv(cache / 'predictions.csv.gz', index=False); fits.to_csv(out / 'pool_fits.csv', index=False)
    metrics = summarize(pred, args.n_boot, meta); assert_coverage(pred, metrics)
    metrics.to_csv(out / 'metrics.csv', index=False)
    status = {'actual_greedy': 'NOT_AVAILABLE', 'reason': 'No R-A saved full-vocabulary greedy continuations; forced-choice LO is pair-conditional',
              'probe': 'TH2-F1 pool256 LR at L42', 'rows': len(pred), 'facts': pred.dataset.nunique(),
              'samples': 'PREPARED_NOT_RUN', 'judge': 'NOT_RUN', **meta}
    write_json(out / 'status.json', status)
    elapsed = time.monotonic() - started
    render_report(metrics, pred, out, meta, elapsed)
    with (out / 'compute.jsonl').open('a') as f: f.write(json.dumps({'stage': 'run', 'wall_s': elapsed, 'pod_hours': 0, 'gpu_hours': 0, 'n_boot': args.n_boot, **meta})+'\n')
    with (out / 'log.md').open('a') as f: f.write(f'- {meta["timestamp"]} CPU complete: `python -m projects.g_agreement.r_bench.remainder_r3 --stage run --n-boot {args.n_boot}`; {elapsed:.1f}s; {len(pred)} items; 0 GPU/pod hours.\n')
    print(json.dumps(status), flush=True)

if __name__ == '__main__': main()
