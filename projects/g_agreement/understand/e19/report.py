"""Offline E19 report: immutable scores, paired changes and all registered cells.

The three random-direction slopes yield a sparse empirical percentile, not a
95% hypothesis test. No score orientation is fitted or flipped in this report.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from projects.g_agreement.blindspot import protocol as P

ROWS = ('prose_paren', 'python_string', 'table_role', 'python_depth', 'prose_sentiment')
STRUCTURE = ROWS[:4]
ALPHAS = (-4, -2, -1, 0, 1, 2, 4)
SEED = 20261025
RANDOM = tuple('random_'+str(seed) for seed in (20261025, 20261026, 20261027))
METRICS = ('asked_score', 'continuation_score', 'projection_preanswer', 'projection_answer_mean')


def arms(row):
    return ('own', *RANDOM, 'donor') + (('content',) if row in STRUCTURE else ())


def _read(path):
    return json.loads(Path(path).read_text())


def _expected(expected_items, records, expected_n):
    """Normalize a frozen metadata list or a per-row mapping; never infer labels."""
    if expected_items is None:
        expected_items = list({(r['row'], r['item_id']): {
            'row': r['row'], 'item_id': r['item_id'], 'cluster': r['cluster']}
            for r in records}.values())
    elif isinstance(expected_items, dict):
        expected_items = [{**item, 'row': row} for row, items in expected_items.items() for item in items]
    rows = {row: {} for row in ROWS}
    for item in expected_items:
        row, key = item.get('row', item.get('feature')), item.get('item_id', item.get('id'))
        cluster = item.get('cluster')
        if row not in rows or not isinstance(key, str) or not key or not isinstance(cluster, str) or not cluster:
            raise ValueError('expected item requires registered row, item ID and template cluster')
        if key in rows[row]:
            raise ValueError('duplicate expected item')
        rows[row][key] = cluster
    if any(len(items) != expected_n for items in rows.values()):
        raise ValueError('expected population must contain every registered row and item')
    if expected_n == 84 and any(len(set(items.values())) != 6 for items in rows.values()):
        raise ValueError('W1 test population requires six frozen template clusters per row')
    return rows


def _validate(records, expected):
    lookup = {}
    for record in records:
        row, key, arm, alpha = (record[k] for k in ('row', 'item_id', 'arm', 'alpha'))
        if row not in expected or key not in expected[row] or arm not in arms(row) or isinstance(alpha, bool) or alpha not in ALPHAS:
            raise ValueError('unknown row/item/arm/alpha in sealed scores')
        if record['cluster'] != expected[row][key]:
            raise ValueError('score cluster differs from frozen template cluster')
        cell = (row, key, arm, alpha)
        if cell in lookup:
            raise ValueError('duplicate score cell')
        for metric in METRICS:
            value = record[metric]
            if value is None and metric == 'continuation_score':
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
                raise ValueError('nonfinite, missing or nonscalar '+metric)
        if row == 'prose_sentiment' and record['continuation_score'] is not None:
            raise ValueError('sentiment has no frozen E15 continuation pair')
        lookup[cell] = record
    return lookup


def _weights(groups, seed, n_bootstrap):
    groups = np.asarray(groups)
    clusters = sorted(set(groups.tolist()))
    rng = np.random.default_rng(seed)
    selected = rng.integers(0, len(clusters), size=(n_bootstrap, len(clusters)))
    counts = (selected[:, :, None] == np.arange(len(clusters))[None, None, :]).sum(axis=1)
    return counts[:, np.array([clusters.index(g) for g in groups])].astype(np.float64)


def _stats(matrix, weights):
    """Column means and cluster-bootstrap CIs, retaining every missing cell."""
    matrix = np.asarray(matrix, dtype=np.float64)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    finite = np.isfinite(matrix)
    count = finite.sum(axis=0)
    values = np.where(finite, matrix, 0.)
    means = np.divide(values.sum(axis=0), count, out=np.full(len(count), np.nan), where=count > 0)
    denominator = weights @ finite.astype(float)
    samples = np.divide(weights @ values, denominator, out=np.full(denominator.shape, np.nan), where=denominator > 0)
    result = []
    for j, n in enumerate(count):
        valid = samples[np.isfinite(samples[:, j]), j]
        ci = np.quantile(valid, [.025, .975]).tolist() if len(valid) else None
        result.append({'n': int(n), 'mean': float(means[j]) if n else None,
                       'ci95': ci, 'bootstrap_valid': len(valid)})
    return result, samples


def _slopes(matrix):
    alpha = np.asarray(ALPHAS, dtype=float)
    good = np.isfinite(matrix).all(axis=1)
    values = np.full(len(matrix), np.nan)
    values[good] = matrix[good] @ alpha / (alpha @ alpha)
    return values


def analyse_scores(records, expected_items=None, *, expected_n=84, n_bootstrap=2000,
                   seed=SEED, continuation_status=None):
    """Pure CPU API returning (summary, per-item paired-change records).

    Nondecreasing means across all seven doses plus a positive slope define
    movement in the frozen A-positive probe direction. No tolerance, orientation
    search, or uncertainty cutoff is added to the registered prediction.
    """
    if type(n_bootstrap) is not int or n_bootstrap < 1:
        raise ValueError('positive bootstrap count required')
    records = list(records)
    expected = _expected(expected_items, records, expected_n)
    lookup = _validate(records, expected)
    continuation_status = continuation_status or {}
    cells, curves, row_results, paired, donor_offsets = [], [], [], [], []
    primary = {}
    for row_index, row in enumerate(ROWS):
        ids = sorted(expected[row]); groups = [expected[row][key] for key in ids]
        # Reuse identical cluster draws for all arms, doses and endpoints in a row.
        weights = _weights(groups, seed+row_index, n_bootstrap)
        raw = {}; slope_draws = {}
        for arm in arms(row):
            for metric in METRICS:
                raw[arm, metric] = np.array([
                    [lookup.get((row, key, arm, alpha), {}).get(metric, np.nan)
                     if lookup.get((row, key, arm, alpha), {}).get(metric) is not None else np.nan
                     for alpha in ALPHAS] for key in ids], dtype=float)
        for arm in arms(row):
            baseline_arm = 'donor' if arm == 'donor' else 'own'
            for metric in METRICS:
                values = raw[arm, metric]
                baseline = raw[baseline_arm, metric][:, ALPHAS.index(0)]
                delta = values-baseline[:, None]
                means, _ = _stats(values, weights)
                changes, _ = _stats(delta, weights)
                slope, samples = _stats(_slopes(delta), weights)
                slope = slope[0]; slope_draws[arm, metric] = samples[:, 0]
                all_complete = np.isfinite(values).all() and np.isfinite(baseline).all()
                unavailable = metric == 'continuation_score' and not np.isfinite(values).any()
                curve = {'row': row, 'arm': arm, 'metric': metric,
                         'baseline_arm': baseline_arm, 'baseline_alpha': 0,
                         'status': 'UNAVAILABLE' if unavailable else ('COMPLETE' if all_complete else 'PARTIAL'),
                         'n_expected': expected_n, 'n_complete_items': slope['n'],
                         'n_clusters': len(set(groups)), 'slope': slope,
                         'alphas': list(ALPHAS), 'mean_trajectory': [s['mean'] for s in means],
                         'monotonic_nondecreasing': (bool(np.all(np.diff([s['mean'] for s in means]) >= 0))
                                                     if all_complete else None),
                         'orientation': 'frozen A-minus-B; no sign flip'}
                if metric == 'continuation_score':
                    curve['endpoint_contract'] = continuation_status.get(row, 'NOT_SUPPLIED')
                curves.append(curve); primary[row, arm, metric] = curve
                for j, alpha in enumerate(ALPHAS):
                    cells.append({'row': row, 'arm': arm, 'metric': metric, 'alpha': alpha,
                                  'n_expected': expected_n, 'n_observed': means[j]['n'],
                                  'n_paired': changes[j]['n'], 'mean_score': means[j]['mean'],
                                  'mean_score_ci95': means[j]['ci95'],
                                  'mean_paired_change': changes[j]['mean'], 'paired_change_ci95': changes[j]['ci95'],
                                  'baseline_arm': baseline_arm, 'baseline_alpha': 0,
                                  'status': 'UNAVAILABLE' if unavailable else
                                      ('COMPLETE' if changes[j]['n'] == expected_n else 'PARTIAL'),
                                  'bootstrap_valid': changes[j]['bootstrap_valid']})
            for i, key in enumerate(ids):
                for j, alpha in enumerate(ALPHAS):
                    rec = {'row': row, 'item_id': key, 'cluster': groups[i], 'arm': arm, 'alpha': alpha,
                           'baseline_arm': baseline_arm, 'baseline_alpha': 0,
                           'score_record_present': (row, key, arm, alpha) in lookup}
                    for metric in METRICS:
                        value = raw[arm, metric][i, j]
                        base = raw[baseline_arm, metric][i, ALPHAS.index(0)]
                        rec[metric+'_change'] = float(value-base) if np.isfinite(value) and np.isfinite(base) else None
                        if arm == 'donor':
                            own_base = raw['own', metric][i, ALPHAS.index(0)]
                            rec[metric+'_donor_zero_minus_own_zero'] = float(base-own_base) if np.isfinite(base) and np.isfinite(own_base) else None
                    paired.append(rec)
        # Donor replacement and subsequent steering are distinct contrasts.
        for metric in METRICS:
            value = raw['donor', metric][:, ALPHAS.index(0)]-raw['own', metric][:, ALPHAS.index(0)]
            stats, _ = _stats(value, weights)
            donor_offsets.append({'row': row, 'metric': metric, 'contrast': 'donor_alpha0_minus_own_alpha0', **stats[0]})
        own = primary[row, 'own', 'asked_score']
        random = [primary[row, arm, 'asked_score'] for arm in RANDOM]
        evaluable = own['status'] == 'COMPLETE' and all(r['status'] == 'COMPLETE' for r in random)
        random_slopes = [r['slope']['mean'] for r in random]
        quantile = float(np.quantile(random_slopes, .95, method='linear')) if evaluable else None
        positive = own['slope']['mean'] is not None and own['slope']['mean'] > 0
        criterion = bool(own['monotonic_nondecreasing'] and positive and own['slope']['mean'] > quantile) if evaluable else None
        difference_ci = None
        if evaluable:
            bootstrap_difference = slope_draws['own', 'asked_score']-np.quantile(
                np.stack([slope_draws[arm, 'asked_score'] for arm in RANDOM]), .95, axis=0, method='linear')
            difference_ci = np.quantile(bootstrap_difference, [.025, .975]).tolist()
        continuation = primary[row, 'own', 'continuation_score']
        row_results.append({'row': row, 'role': 'structure' if row in STRUCTURE else 'positive_content_control',
            'asked_own_slope': own['slope'], 'asked_monotonic_nondecreasing': own['monotonic_nondecreasing'],
            'asked_positive_direction': positive if own['status'] == 'COMPLETE' else None,
            'random_slopes': dict(zip(RANDOM, random_slopes)), 'random_slope_q95': quantile,
            'own_minus_random_q95': own['slope']['mean']-quantile if evaluable else None,
            'own_minus_random_q95_ci95': difference_ci,
            'registered_pattern_observed': criterion,
            'continuation_own_slope': continuation['slope'],
            'continuation_status': continuation['status'],
            'disconnected_classification': 'DESCRIPTIVE_ONLY_NO_ADDITIONAL_THRESHOLD',
            'asked_slope_within_empirical_random_range':
                bool(min(random_slopes) <= own['slope']['mean'] <= max(random_slopes)) if evaluable else None})
    structure = [r for r in row_results if r['row'] in STRUCTURE]
    count = sum(r['registered_pattern_observed'] is True for r in structure)
    missing = sum(r['registered_pattern_observed'] is None for r in structure)
    held = True if count >= 3 else (False if count+missing < 3 else None)
    expected_cells = sum(len(arms(row))*expected_n*len(ALPHAS) for row in ROWS)
    summary = {'experiment': 'E19', 'exploratory': True, 'rows': row_results, 'curves': curves, 'cells': cells,
        'donor_baseline_offsets': donor_offsets, 'n_score_records': len(records),
        'n_expected_score_records': expected_cells, 'n_missing_score_records': expected_cells-len(records),
        'population_status': 'COMPLETE' if len(records) == expected_cells else 'PARTIAL',
        'prediction': {'pathway_underweighted_observed': held, 'state_rows_observed': count,
                       'state_rows_total': 4, 'state_rows_not_evaluable': missing,
                       'requirement': 'at least 3 of 4 state rows: all-seven-dose monotonic A-positive asked movement and own slope above empirical random q95'},
        'positive_control': next(r for r in row_results if r['row'] == 'prose_sentiment'),
        'method': {'alphas': list(ALPHAS), 'slope': 'OLS of the seven paired alpha-minus-zero changes against alpha, with intercept; average per-item slopes',
            'monotonicity': 'nondecreasing seven-dose mean asked trajectory and positive slope; no sign flips or fitted tolerance',
            'bootstrap': 'percentile95; resample W1 template clusters with replacement; same draws for all arms and alphas within row',
            'bootstrap_replicates': n_bootstrap, 'seed': seed, 'row_seed': 'seed plus fixed registered row index',
            'random_baseline': 'three seeded unit directions; empirical 95th percentile using linear interpolation',
            'random_percentile_limitation': 'Only three direction slopes: the 95th percentile is sparse and is not a calibrated 95% hypothesis test or a random-direction population bound.',
            'donor_baseline': 'donor steering uses donor alpha0; donor alpha0 minus own alpha0 is a separate replacement effect',
            'projection': 'row own probe projection one decoder layer after intervention; preanswer and mean true-answer positions retained separately',
            'disconnected': 'No added statistical cutoff: display asked/random and continuation trajectories together; no automatic disconnected verdict.'}}
    return summary, paired


def verify(scores, inputs, freeze):
    """Verify every upstream binding before parsing the score JSONL."""
    from .freeze import load_freeze
    scores, inputs, freeze = map(Path, (scores, inputs, freeze))
    seal = P.verify(scores, 'SCORE_SEAL.json')
    required = {'scores.jsonl', 'provenance.json', 'manifest.json', 'RUN_STATUS.json'}
    if seal.get('status') != 'SCORES_SEALED_EXPLORATORY_E19' or not required <= set(seal['files']):
        raise ValueError('complete E19 score-file seal coverage required, including explicit partial status')
    input_seal = P.verify(inputs, 'INPUT_SEAL.json')
    if not {'items.input.jsonl', 'continuation_pairs.json', 'provenance.json'} <= set(input_seal['files']):
        raise ValueError('E19 input seal missing analysis metadata')
    frozen, directions = load_freeze(freeze)
    prov = _read(scores/'provenance.json')
    if (prov.get('experiment') != 'E19' or prov.get('input_seal_sha256') != P.sha(inputs/'INPUT_SEAL.json')
            or prov.get('freeze_seal_sha256') != P.sha(freeze/'FREEZE_SEAL.json')
            or not isinstance(prov.get('source_files'), dict) or not prov['source_files']
            or not isinstance(prov.get('freeze_commit'), str) or len(prov['freeze_commit']) != 40
            or any(c not in '0123456789abcdef' for c in prov['freeze_commit'])):
        raise ValueError('E19 capture/input/dev-freeze provenance mismatch')
    manifest = _read(scores/'manifest.json')
    expected = manifest['expected_items']
    source_items = P.rows(inputs/'items.input.jsonl')
    ids = {(r.get('row', r.get('feature')), r.get('item_id', r.get('id'))) for r in expected}
    if ids != {(r['feature'], r['id']) for r in source_items} or len(ids) != len(expected):
        raise ValueError('score manifest population differs from frozen E19 inputs')
    clusters = {(r['feature'], r['id']): r.get('cluster') for r in source_items}
    if any(not clusters[key] for key in clusters) or any(
            item.get('cluster') != clusters[(item.get('row', item.get('feature')), item.get('item_id', item.get('id')))]
            for item in expected):
        raise ValueError('manifest template clusters differ from frozen input metadata')
    input_prov = _read(inputs/'provenance.json')
    if frozen['source']['e3_input_seal_sha256'] != input_prov.get('source_e3_input_seal_sha256'):
        raise ValueError('E19 capture and dev directions have different E3 sources')
    return {'seal': seal, 'provenance': prov, 'manifest': manifest, 'freeze': frozen,
            'directions': directions, 'run_status': _read(scores/'RUN_STATUS.json'),
            'continuation': _read(inputs/'continuation_pairs.json')}


def _fmt(value):
    return 'NA' if value is None else f'{value:.5g}'


def _custody_telemetry(scores, score_seal):
    """Optional operator accounting is separate from immutable scientific data."""
    path = Path(scores)/'budget.json'
    if not path.exists():
        return {'status': 'NOT_AVAILABLE', 'compliance_claim': False}
    result = {'path': str(path.resolve()), 'sha256': P.sha(path),
              'covered_by_primary_score_seal': 'budget.json' in score_seal['files'],
              'source': 'operator custody telemetry; not an independent provider audit',
              'compliance_claim': False}
    try:
        values = _read(path)
    except (ValueError, OSError) as error:
        result.update(status='UNREADABLE_TELEMETRY', error=str(error))
        return result
    result['values'] = values
    elapsed, cap, overrun = (values.get(k) for k in ('science_seconds', 'science_cap_seconds', 'cap_overrun_seconds'))
    finite = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool) and np.isfinite(value)
    exceeded = (finite(overrun) and overrun > 0) or (finite(elapsed) and finite(cap) and elapsed > cap)
    result['status'] = 'CAP_OVERRUN_REPORTED' if exceeded else 'NO_CAP_OVERRUN_REPORTED_NOT_INDEPENDENTLY_VERIFIED'
    return result


def _markdown(summary):
    prediction = summary['prediction']; held = prediction['pathway_underweighted_observed']
    verdict = ('The registered pathway prediction held in the observed data.' if held is True else
               'The registered pathway prediction did not hold in the observed data.' if held is False else
               'The registered pathway prediction is unresolved because required cells are missing.')
    lines = ["Prediction: the Oracle reader's pathway exists but is under-weighted: monotonic asked movement with own-direction slope above the random-direction 95th percentile on at least three of four state rows.",
             '', verdict, f"Observed: {prediction['state_rows_observed']}/4 state rows; {prediction['state_rows_not_evaluable']} not evaluable. This is exploratory.", '',
             '| Row | Own asked slope | Random q95 | Monotonic | Registered pattern | Own continuation slope |',
             '|---|---:|---:|---|---|---:|']
    for row in summary['rows']:
        lines.append(f"| {row['row']} | {_fmt(row['asked_own_slope']['mean'])} | {_fmt(row['random_slope_q95'])} | {row['asked_monotonic_nondecreasing']} | {row['registered_pattern_observed']} | {_fmt(row['continuation_own_slope']['mean'])} |")
    control = summary['positive_control']
    lines += ['', f"Positive control (`prose_sentiment`): positive asked slope = {control['asked_positive_direction']}; seven-dose monotonicity = {control['asked_monotonic_nondecreasing']}. The content-control prediction is assessed separately from the four-state-row count.",
              '', '**Random baseline:** '+summary['method']['random_percentile_limitation'],
              '', 'The continuation endpoint is unavailable when E15 supplied no dev-valid pair. No sentiment continuation pair is invented. A disconnected-pathway interpretation remains descriptive: the report provides signed asked/random slopes and continuation changes without adding an unregistered movement threshold.',
              '', f"Score coverage: {summary['n_score_records']}/{summary['n_expected_score_records']} records. Missing cells remain in the tables. Every paired change uses the same item at alpha zero; donor steering uses its donor-injected zero baseline, with donor replacement shown separately.",
              '', 'All four measures, all doses, and all control arms are in `cells.csv`; curve slopes and 95% cluster-bootstrap intervals are in `summary.json`. Preanswer and answer projection changes measure whether the intervention reached the next layer. No sign was flipped.']
    if summary.get('capture_run_status') is not None:
        lines += ['', 'Capture status: `'+str(summary['capture_run_status'])+'`.']
    custody = summary.get('custody_telemetry', {})
    if custody.get('status') == 'CAP_OVERRUN_REPORTED':
        values = custody['values']
        lines += ['', f"**Budget overrun reported:** operator telemetry records {_fmt(values.get('science_seconds'))} s through sealing against a {_fmt(values.get('science_cap_seconds'))} s science cap. The scientific results are retained; this report makes no claim that the run stayed within budget."]
    if custody.get('sha256'):
        lines += ['', 'Custody telemetry is '+('covered' if custody['covered_by_primary_score_seal'] else '**not covered**')+
                  ' by the primary score seal. Its copied contents and SHA256 are retained separately in `summary.json`; they are not an independent provider-custody audit.']
    return '\n'.join(lines)+'\n'


def generate(scores, inputs, freeze, out, cache_out):
    scores, inputs, freeze, out, cache_out = map(Path, (scores, inputs, freeze, out, cache_out))
    if out.exists() or cache_out.exists():
        raise FileExistsError('refusing to overwrite an E19 analysis or paired-change cache')
    verified = verify(scores, inputs, freeze)
    records = P.rows(scores/'scores.jsonl')
    statuses = {row: spec['primary_status'] for row, spec in verified['continuation']['rows'].items()}
    for record in records:
        direction = verified['directions'].get(record['row'])
        if direction is None or record.get('layer') != direction['layer'] or record.get('sigma') != direction['sigma']:
            raise ValueError('scored intervention differs from the dev-only layer/direction scale freeze')
        if record['continuation_score'] is not None and statuses[record['row']] != 'EVALUABLE':
            raise ValueError('primary continuation score lacks E15 dev-valid pair authorization')
    summary, paired = analyse_scores(records, verified['manifest']['expected_items'], continuation_status=statuses)
    summary['capture_run_status'] = verified['run_status']
    summary['custody_telemetry'] = _custody_telemetry(scores, verified['seal'])
    summary['provenance'] = {**verified['provenance'],
        'score_seal_sha256': P.sha(scores/'SCORE_SEAL.json'),
        'analysis_source_sha256': P.sha(Path(__file__)),
        'selected_layers': {row: spec['layer'] for row, spec in verified['directions'].items()},
        'selected_sigmas': {row: spec['sigma'] for row, spec in verified['directions'].items()}}
    out.mkdir(parents=True); cache_out.mkdir(parents=True)
    P.jsonl(cache_out/'paired_items.jsonl', paired)
    summary['paired_items'] = {'path': str((cache_out/'paired_items.jsonl').resolve()),
                              'sha256': P.sha(cache_out/'paired_items.jsonl'), 'n': len(paired)}
    P.dump(out/'summary.json', summary)
    with (out/'cells.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary['cells'][0]))
        writer.writeheader()
        for cell in summary['cells']:
            writer.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in cell.items()})
    (out/'RESULTS.md').write_text(_markdown(summary))
    P.dump(out/'ANALYSIS_SEAL.json', {'status': 'E19_EXPLORATORY_ANALYSIS_SEALED',
        'files': {name: P.sha(out/name) for name in ('summary.json', 'cells.csv', 'RESULTS.md')}})
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('scores', 'inputs', 'freeze', 'out', 'cache-out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(argv)
    result = generate(**vars(args))
    print(json.dumps({'experiment': 'E19', 'prediction': result['prediction'], 'population_status': result['population_status']}))


if __name__ == '__main__':
    main()
