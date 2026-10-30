"""§110 once-only E17 analysis; operational choices frozen before capture.

Each feature/channel gets one W1 logistic probe (lambda=1e-3), fitted on
pooled dev cells only. Test predictions never participate in fitting/scaling.
Both frozen E15 pairs are averaged, without new validity selection or sign flips.
The two late-minus-early-long comparisons remain separate; a row must satisfy
both. Holm tests three row-level positive-direction hypotheses, using the maximum
of the two late bootstrap tail probabilities for the conjunction. The >=.10
effect-size and <=.05 source-flatness checks are separate point-estimate criteria;
flatness is not a formal equivalence claim. Window contrasts/CIs are descriptive,
and no new window-effect cutoff is introduced. Item bootstrap draws preserve
twins and share lexical-instance draws across cells, with dev fits held fixed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from projects.g_agreement.blindspot import protocol as P
from . import e17_run as R

SEED = 20261025
BOOT = 2000
CELLS = {
    'prose_paren': ('short_early', 'short_late', 'long_early', 'long_late'),
    'python_string': ('short_early', 'short_late', 'long_early', 'long_late'),
    'list_depth': ('mid_item', 'line_end'),
}
VALUES = {'prose_paren': ('inside', 'outside'), 'python_string': ('inside', 'outside'),
          'list_depth': ('shallow', 'deep')}
METRIC_SPEC = {
    'seed': SEED, 'bootstrap_samples': BOOT,
    'probe': 'one per feature/channel; pooled dev cells; W1 mats.probes.fit_logreg lambda=1e-3, default200LBFGS iterations, train-only standardization',
    'channels': ['source_probe', 'window_probe', 'continuation', 'asked'],
    'continuation': 'mean of both already frozen E15 pairs; no E17 validity selection; no sign flip',
    'bootstrap': 'resample64test lexical_id clusters with replacement, preserving A/B and sharing identical draws across cells and channels; fixed dev fits',
    'late_aggregation': 'both short_late-long_early and long_late-long_early must hold separately; no pooled late score',
    'list_contrast': 'line_end-mid_item',
    'p_value': '(1+number of bootstrap contrasts<=0)/(2000+1); one-sided percentile-bootstrap tail approximation',
    'row_p_value': 'maximum of both late contrast p-values for paren/string; single contrast p for list',
    'multiplicity': 'Holm step-down across exactly3 rows, alpha0.05; report adjusted p',
    'lens_direction_holds': 'every registered contrast point>=0.10, paired95%percentile CI lower>0, and row Holm-adjusted p<=0.05',
    'source_flat': 'every matching source contrast absolute point<=0.05; show CI, no equivalence claim',
    'window': 'report corresponding signed differences and95%CIs; direction positive is a descriptive component, no effect-size/significance cutoff',
    'asked': 'true-arm mean-pair AUROC<=0.60 in every cell',
    'outcome': 'row structural direction = lens_direction_holds and source_flat; spans direction requires both paren and string, list direction requires list; both=SUPPORTED, one=PARTIAL, neither=NOT_SUPPORTED; window/asked predictions assessed separately and full prediction held only if all components hold',
    'controls': 'report every frozen candidate pair and mean for true/random_donor/opposite_swap; signed recipient-label orientation, no control exclusion rule',
    'across_cell_figure': 'all10 cell point estimates; source/window AUROC versus continuation AUROC; Pearson/Spearman descriptive only, no p-value or selection',
}


def auroc(scores, y):
    """Mann-Whitney AUROC, vectorized over leading dimensions, with average ties."""
    from scipy.stats import rankdata
    scores, y = np.asarray(scores, float), np.asarray(y, bool)
    if scores.shape[-1] != len(y) or not np.isfinite(scores).all() or not 0 < y.sum() < len(y):
        raise ValueError('invalid finite two-class AUROC input')
    ranks = rankdata(scores, axis=-1, method='average')
    n = int(y.sum())
    result = (ranks[..., y].sum(-1) - n * (n + 1) / 2) / (n * (len(y) - n))
    return float(result) if result.ndim == 0 else result


def paired_resamples(n_pairs, n_boot=BOOT, seed=SEED):
    """Each row resamples complete [A,B] pairs in common lexical-id order."""
    if n_pairs <= 0 or n_boot <= 0:
        raise ValueError('positive bootstrap dimensions required')
    draws = np.random.default_rng(seed).integers(n_pairs, size=(n_boot, n_pairs))
    return np.stack((2 * draws, 2 * draws + 1), axis=-1).reshape(n_boot, 2 * n_pairs)


def estimate(scores, y, draws):
    scores, y = np.asarray(scores, float), np.asarray(y, bool)
    if not np.array_equal(y, np.tile([True, False], len(y) // 2)):
        raise ValueError('lexical ordering must retain A then B')
    boots = auroc(scores[draws], y)
    return {'auroc': auroc(scores, y), 'ci95': np.quantile(boots, [.025, .975]).tolist()}, boots


def contrast(high, low, high_boot, low_boot):
    samples = np.asarray(high_boot) - np.asarray(low_boot)
    return {'difference': float(high - low), 'ci95': np.quantile(samples, [.025, .975]).tolist(),
            'p_one_sided_bootstrap': float((1 + np.count_nonzero(samples <= 0)) / (len(samples) + 1))}


def holm(p_values):
    """Holm adjusted p-values in input order, retaining exactly all three rows."""
    p = np.asarray(p_values, float)
    if p.shape != (3,) or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('exactly three finite row p-values required')
    order = np.argsort(p, kind='stable')
    adjusted = np.empty(3)
    adjusted[order] = np.minimum(1, np.maximum.accumulate(p[order] * np.arange(3, 0, -1)))
    return adjusted.tolist()


def fit_dev_scores(vectors, items, labels, feature, fit_fn=None):
    """One dev-only fit predicts every item of a feature; never fit on test."""
    import torch
    if fit_fn is None:
        import common  # establishes the pinned mats package import path
        from mats.probes import fit_logreg as fit_fn
    selected = [i for i, x in enumerate(items) if x['feature'] == feature]
    dev = [i for i in selected if items[i]['split'] == 'dev']
    test = [i for i in selected if items[i]['split'] == 'test']
    if not dev or not test or {items[i]['cluster'] for i in dev} & {items[i]['cluster'] for i in test}:
        raise ValueError('dev/test probe split leakage')
    x = torch.as_tensor(np.asarray(vectors), dtype=torch.float32)
    y = torch.tensor([labels[items[i]['id']]['value'] == VALUES[feature][0] for i in dev], dtype=torch.int64)
    if set(y.tolist()) != {0, 1}:
        raise ValueError('dev probe requires both frozen values')
    model = fit_fn(x[dev], y, lam=1e-3)
    result = model.decision(x[selected]).detach().cpu().numpy()
    if result.shape != (len(selected),) or not np.isfinite(result).all():
        raise ValueError('invalid probe predictions')
    return {items[i]['id']: float(s) for i, s in zip(selected, result)}, {
        'feature': feature, 'n_dev': len(dev), 'n_test': len(test),
        'dev_ids': [items[i]['id'] for i in dev], 'test_ids': [items[i]['id'] for i in test],
        'train_clusters': sorted({items[i]['cluster'] for i in dev}),
        'test_clusters': sorted({items[i]['cluster'] for i in test}),
        'fit_split': 'dev', 'lambda': 1e-3,
    }, model


def verify_prelabel(bank, outputs):
    """Verify seals, source, population and donor algebra before opening labels."""
    bank, outputs = Path(bank), Path(outputs)
    items, _, _ = R.inputs(bank)
    seal = P.verify(outputs, 'SCORE_SEAL.json')
    required = {'source44.npy', 'window44.npy', 'items.order.json', 'scores.jsonl',
                'provenance.json', 'FORECAST.json', 'EXPERIMENT_CLOCK.json', 'CAPTURE_SEAL.json'}
    if seal.get('status') != 'E17_CHANNELS_SEALED_BEFORE_LABEL_JOIN' or not required <= set(seal['files']):
        raise ValueError('complete E17 output seal required')
    provenance = json.loads((outputs / 'provenance.json').read_text())
    if (provenance.get('experiment') != 'E17'
            or provenance.get('input_seal_sha256') != P.sha(bank / 'INPUT_SEAL.json')
            or provenance.get('manifest_sha256') != P.sha(bank / 'manifest.json')
            or provenance.get('source_files') != R.source_hashes()):
        raise ValueError('E17 frozen source/input lineage mismatch')
    order = json.loads((outputs / 'items.order.json').read_text())
    if order != [x['id'] for x in items]:
        raise ValueError('activation order does not match frozen items')
    arrays = {key: np.load(outputs / name, allow_pickle=False) for key, name in
              (('source_probe', 'source44.npy'), ('window_probe', 'window44.npy'))}
    if any(h.shape != (1920, 5120) or not np.isfinite(h).all() for h in arrays.values()):
        raise ValueError('complete finite block44/AR44 arrays required')
    raw = P.rows(outputs / 'scores.jsonl')
    R.validate_grid(items, raw)
    lookup = {(r['id'], r['channel'], r['arm']): r for r in raw}
    for x in items:
        for channel in R.CHANNELS:
            for arm, donor_key in (('true', None), ('random_donor', 'random_donor_id'), ('opposite_swap', 'opposite_donor_id')):
                r = lookup[x['id'], channel, arm]
                if r['feature'] != x['feature'] or r['cell'] != x['cell'] or r.get('reader') != 'olens' or r.get('layer') != 44:
                    raise ValueError('score metadata mismatch')
                if donor_key and (r.get('donor_id') != x[donor_key] or r['scores'] != lookup[x[donor_key], channel, 'true']['scores']):
                    raise ValueError('donor reindexing differs from frozen plan')
    P.verify(outputs, 'CAPTURE_SEAL.json')
    return items, arrays, lookup


def label_join(bank, path, items):
    bank, path = Path(bank), Path(path)
    if path.resolve().is_relative_to(bank.resolve()):
        raise ValueError('labels must remain outside staged bank')
    manifest = json.loads((bank / 'manifest.json').read_text())
    if P.sha(path) != manifest['labels_sha256']:
        raise ValueError('frozen E17 label hash mismatch')
    rows = P.rows(path)
    labels = {x['id']: x for x in rows}
    if len(labels) != len(rows) or set(labels) != {x['id'] for x in items}:
        raise ValueError('complete unique label grid required')
    lexical = {}
    for x in items:
        lab = labels[x['id']]
        if any(lab[k] != x[k] for k in ('feature', 'cell', 'split', 'cluster', 'pair_id', 'lexical_id')) or lab['value'] not in VALUES[x['feature']]:
            raise ValueError('label metadata disagrees with frozen inputs')
        if lab['label'] != int(lab['value'] == VALUES[x['feature']][0]):
            raise ValueError('integer label disagrees with frozen value orientation')
        if not isinstance(lab['lexical_id'], str) or not lab['lexical_id']:
            raise ValueError('frozen lexical bootstrap ID required')
        key = x['feature'], x['cell'], x['split'], lab['lexical_id']
        lexical.setdefault(key, []).append(lab['value'])
    if any(sorted(v) != sorted(VALUES[k[0]]) for k, v in lexical.items()):
        raise ValueError('each lexical cluster must contain one aligned A/B pair')
    for feature, cells in CELLS.items():
        split_universes = {}
        for split, count in (('dev', 32), ('test', 64)):
            universes = [{key[3] for key in lexical if key[:3] == (feature, cell, split)} for cell in cells]
            if any(len(u) != count or u != universes[0] for u in universes):
                raise ValueError('same complete lexical population required across cells')
            split_universes[split] = universes[0]
        if split_universes['dev'] & split_universes['test']:
            raise ValueError('lexical bootstrap instances leak across dev/test')
    return labels


def acquire_lock(out, outputs):
    out, outputs = Path(out), Path(outputs)
    if out.exists():
        raise ValueError('E17 analysis output exists; never repeat')
    lock = out.with_name(out.name + '.lock.json')
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('x') as stream:
        json.dump({'experiment': 'E17', 'status': 'STARTED',
                   'score_seal_sha256': P.sha(outputs / 'SCORE_SEAL.json')}, stream)
    return lock


def decision(rows):
    adjusted = holm([r['p_row_one_sided'] for r in rows])
    for row, p in zip(rows, adjusted):
        row['p_holm'] = p
        row['lens_direction_holds'] = bool(p <= .05 and all(c['channels']['continuation']['difference'] >= .10
            and c['channels']['continuation']['ci95'][0] > 0 for c in row['contrasts']))
        row['source_flat'] = all(abs(c['channels']['source_probe']['difference']) <= .05 for c in row['contrasts'])
        row['window_direction_positive_descriptive'] = all(c['channels']['window_probe']['difference'] > 0 for c in row['contrasts'])
        row['direction_holds'] = row['lens_direction_holds'] and row['source_flat']
    by_feature = {r['feature']: r for r in rows}
    span = all(by_feature[f]['direction_holds'] for f in ('prose_paren', 'python_string'))
    listing = by_feature['list_depth']['direction_holds']
    full = span and listing and all(r['window_direction_positive_descriptive'] and r['asked_all_cells_at_most_060'] for r in rows)
    return {'span_direction_holds': span, 'list_direction_holds': listing,
            'horizon_direction_outcome': 'SUPPORTED' if span and listing else ('PARTIAL' if span or listing else 'NOT_SUPPORTED'),
            'full_prediction_held': bool(full),
            'plain_assessment': 'The full prediction held.' if full else ('The directional prediction held, but the full prediction did not hold.' if span and listing else ('The prediction partly held.' if span or listing else 'The prediction did not hold.')),
            'window_no_numeric_cutoff_added': True, 'source_flatness_is_point_check_not_equivalence_test': True}


def correlation_data(rows):
    """Ten-cell descriptive association; repeated cells are not independent tests."""
    from scipy.stats import spearmanr
    points = [{'feature': row['feature'], 'cell': cell,
        'source_probe': r['channels']['source_probe']['auroc'],
        'window_probe': r['channels']['window_probe']['auroc'],
        'continuation': r['channels']['continuation']['true']['auroc']}
        for row in rows for cell, r in row['cells'].items()]
    associations = {}
    y = np.array([p['continuation'] for p in points])
    for channel in ('source_probe', 'window_probe'):
        x = np.array([p[channel] for p in points])
        available = np.ptp(x) > 0 and np.ptp(y) > 0
        associations[channel] = {'pearson': float(np.corrcoef(x, y)[0, 1]) if available else None,
            'spearman': float(spearmanr(x, y).statistic) if available else None,
            'status': 'DESCRIPTIVE_ONLY_NO_INDEPENDENT_CELL_TEST' if available else 'UNDEFINED_CONSTANT_CHANNEL'}
    return {'points': points, 'associations': associations}


def plot_correlations(data, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = {'prose_paren': '#235789', 'python_string': '#d66a2c', 'list_depth': '#287d52'}
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
    for ax, channel in zip(axes, ('source_probe', 'window_probe')):
        for feature in CELLS:
            points = [p for p in data['points'] if p['feature'] == feature]
            ax.scatter([p[channel] for p in points], [p['continuation'] for p in points],
                       color=colors[feature], label=feature, s=44)
            for point in points:
                ax.annotate(point['cell'], (point[channel], point['continuation']),
                            xytext=(4, 4), textcoords='offset points', fontsize=6)
        ax.set(xlim=(-.03, 1.03), ylim=(-.03, 1.03), xlabel=channel.replace('_', ' ') + ' AUROC')
        ax.grid(alpha=.2)
        rho = data['associations'][channel]['spearman']
        ax.set_title('Spearman = ' + ('undefined' if rho is None else f'{rho:.3f}') + ' (descriptive)')
    axes[0].set_ylabel('Oracle continuation AUROC')
    axes[1].legend(loc='lower right', fontsize=8)
    fig.suptitle('E17: all10 cells; shared items and fitted probes, no independent-cell test')
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def analyse(bank, outputs, label_path, out):
    bank, outputs, label_path, out = map(Path, (bank, outputs, label_path, out))
    if out.exists() or out.with_name(out.name + '.lock.json').exists():
        raise ValueError('E17 analysis output/lock already exists; never repeat')
    items, arrays, scores = verify_prelabel(bank, outputs)
    labels = label_join(bank, label_path, items)
    acquire_lock(out, outputs)
    probes, fits, parameters = {}, [], {}
    for feature in CELLS:
        for channel, h in arrays.items():
            values, fit, model = fit_dev_scores(h, items, labels, feature)
            probes[feature, channel] = values
            fits.append({**fit, 'channel': channel})
            key = feature + '__' + channel
            parameters[key + '__w'] = model.w.detach().cpu().numpy()
            parameters[key + '__mu'] = model.mu.detach().cpu().numpy()
            parameters[key + '__sd'] = model.sd.detach().cpu().numpy()
            parameters[key + '__b'] = np.array(model.b)
    results, predictions = [], []
    for feature, names in CELLS.items():
        draws = paired_resamples(64)
        cell_results, boot = {}, {}
        for cell in names:
            selected = [x for x in items if x['feature'] == feature and x['cell'] == cell and x['split'] == 'test']
            selected.sort(key=lambda x: (labels[x['id']]['lexical_id'], labels[x['id']]['value'] != VALUES[feature][0]))
            ids = [x['id'] for x in selected]
            y = np.array([labels[i]['value'] == VALUES[feature][0] for i in ids])
            vectors = {channel: np.array([probes[feature, channel][i] for i in ids]) for channel in arrays}
            result = {'n_test_items': len(ids), 'n_test_pairs': len(ids) // 2, 'channels': {}}
            for channel, values in vectors.items():
                result['channels'][channel], boot[cell, channel] = estimate(values, y, draws)
            for channel in R.CHANNELS:
                arms = {}
                for arm in R.ARMS:
                    matrix = np.array([scores[i, channel, arm]['scores'] for i in ids])
                    values = matrix.mean(1)
                    entry, samples = estimate(values, y, draws)
                    entry['per_pair'] = [estimate(matrix[:,j], y, draws)[0] for j in range(2)]
                    arms[arm] = entry
                    boot[cell, channel, arm] = samples
                    if arm == 'true':
                        vectors[channel] = values
                        boot[cell, channel] = samples
                arms['true_minus_random'] = contrast(arms['true']['auroc'], arms['random_donor']['auroc'],
                    boot[cell, channel, 'true'], boot[cell, channel, 'random_donor'])
                result['channels'][channel] = arms
            cell_results[cell] = result
            for j, item in enumerate(selected):
                predictions.append({'id': item['id'], 'feature': feature, 'cell': cell,
                    'lexical_id': labels[item['id']]['lexical_id'], 'value': labels[item['id']]['value'],
                    **{channel: float(values[j]) for channel, values in vectors.items()},
                    'frozen_pair_scores': {channel: {arm: scores[item['id'], channel, arm]['scores']
                        for arm in R.ARMS} for channel in R.CHANNELS}})
        pairs = [('line_end', 'mid_item')] if feature == 'list_depth' else [('short_late', 'long_early'), ('long_late', 'long_early')]
        contrasts = []
        for high, low in pairs:
            channels = {}
            for channel in METRIC_SPEC['channels']:
                high_stat, low_stat = cell_results[high]['channels'][channel], cell_results[low]['channels'][channel]
                if channel in R.CHANNELS:
                    high_stat, low_stat = high_stat['true'], low_stat['true']
                channels[channel] = contrast(high_stat['auroc'], low_stat['auroc'], boot[high, channel], boot[low, channel])
            contrasts.append({'high': high, 'low': low, 'channels': channels})
        results.append({'feature': feature, 'cells': cell_results, 'contrasts': contrasts,
            'p_row_one_sided': max(c['channels']['continuation']['p_one_sided_bootstrap'] for c in contrasts),
            'asked_all_cells_at_most_060': all(r['channels']['asked']['true']['auroc'] <= .60 for r in cell_results.values())})
    summary = decision(results)
    correlations = correlation_data(results)
    out.mkdir(parents=True, exist_ok=False)
    metrics = {'experiment': 'E17', 'section': 110, 'status': 'EXPLORATORY', 'metric_spec': METRIC_SPEC,
               'rows': results, 'summary': summary, 'descriptive_across_cell': correlations,
               'score_seal_sha256': P.sha(outputs / 'SCORE_SEAL.json'),
               'input_seal_sha256': P.sha(bank / 'INPUT_SEAL.json'), 'labels_sha256': P.sha(label_path),
               'analysis_source_sha256': P.sha(Path(__file__))}
    P.dump(out / 'metrics.json', metrics)
    P.dump(out / 'probe_fits.json', fits)
    np.savez(out / 'probe_parameters.npz', **parameters)
    P.jsonl(out / 'predictions.jsonl', predictions)
    plot_correlations(correlations, out / 'CELL_CORRELATIONS.svg')
    (out / 'RESULTS.md').write_text(report(metrics))
    names = ('metrics.json', 'probe_fits.json', 'probe_parameters.npz', 'predictions.jsonl', 'CELL_CORRELATIONS.svg', 'RESULTS.md')
    P.dump(out / 'ANALYSIS_SEAL.json', {'status': 'E17_ANALYSIS_COMPLETE', 'files': {n: P.sha(out / n) for n in names}})
    return summary


def report(metrics):
    lines = ['**Prediction (§110):** Oracle native continuation readability rises when the real next16 tokens reveal structure: both late span cells outperform early-long by≥0.10, and list line-end outperforms mid-item by≥0.10, while source-probe differences stay within±0.05. The window channel follows the lens and asked AUROC stays≤0.60 in every cell.', '',
             '**Assessment:** ' + metrics['summary']['plain_assessment'], '',
             'EXPLORATORY. Both E15 pairs are used unchanged. Logistic probes train only on pooled dev cells; all reported AUROCs use held-out template families. CIs use2,000 paired item-cluster resamples, shared across cells. Holm controls the three row-level positive-direction comparisons. The0.10 effect and0.05 flatness criteria apply to point estimates; source flatness is not a formal equivalence result. Window contrasts are descriptive; no new magnitude or significance threshold was added.', '',
             '| Row / cell | Source probe | Next16 AR probe | Oracle continuation | Asked | Random continuation | Opposite continuation |',
             '|---|---|---|---|---|---|---|']
    def fmt(x):
        return f"{x['auroc']:.3f} [{x['ci95'][0]:.3f},{x['ci95'][1]:.3f}]"
    for row in metrics['rows']:
        for cell, r in row['cells'].items():
            c = r['channels']
            lines.append('| ' + ' | '.join([row['feature'] + ' / ' + cell, fmt(c['source_probe']), fmt(c['window_probe']),
                fmt(c['continuation']['true']), fmt(c['asked']['true']), fmt(c['continuation']['random_donor']), fmt(c['continuation']['opposite_swap'])]) + ' |')
    lines += ['', '| Row / contrast | Lens Δ [95% CI] | Source Δ [95% CI] | Window Δ [95% CI] | Row Holm p | Direction held |', '|---|---|---|---|---:|---|']
    def delta(x):
        return f"{x['difference']:+.3f} [{x['ci95'][0]:+.3f},{x['ci95'][1]:+.3f}]"
    for row in metrics['rows']:
        for c in row['contrasts']:
            lines.append('| ' + ' | '.join([row['feature'] + ' / ' + c['high'] + '−' + c['low'],
                delta(c['channels']['continuation']), delta(c['channels']['source_probe']), delta(c['channels']['window_probe']),
                f"{row['p_holm']:.5f}", str(row['direction_holds'])]) + ' |')
    lines += ['', 'Every continuation pair and asked phrasing, all three arms, their CIs, true−random contrasts, and each cell are retained in `metrics.json`; dev/test membership and fitted parameters are retained separately. Controls remain signed against recipient truth and never cause a post-hoc exclusion.', '',
              '![Descriptive across-cell correlations](CELL_CORRELATIONS.svg)', '',
              'The list stimulus uses a shared2-space root offset: current/next items at2 versus6 spaces are top/third level. E15’s unchanged2-versus4-space candidates remain an inherited shallow/deep proxy. Neutral Python twins are outside-string lexical controls and are not promised to be valid executable programs. No result establishes spontaneous generation, and the across-cell correlation is descriptive only.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bank', 'outputs', 'labels', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyse(args.bank, args.outputs, args.labels, args.out), indent=2))


if __name__ == '__main__':
    main()
