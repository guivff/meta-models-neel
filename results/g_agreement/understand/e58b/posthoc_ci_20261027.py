"""POST HOC CPU-only paired item-bootstrap intervals; sealed verdicts stay intact."""
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from common58 import ROOT, HERE, CACHE, ARMS, SEEDS, read, dump, sha, verify, source_verify, require
from cpu_join58 import load_custodied_join, join_records

DRAWS = 2000
SEED = 20261027
METRICS = ('J_damage', 'random_damage_mean5', 'PCA_damage', 'J_minus_random_damage')
OUT = HERE / 'E58B_POSTHOC_CI.json'


def item_damage(rows, records):
    expected = {(row['key'], item['id'], j, arm)
                for row in rows for item in row['test']
                for j in range(len(item['pairs'])) for arm in ARMS}
    keyed = {(x['row'], x['id'], x['pair_index'], x['arm']): x['logodds_A_minus_B'] for x in records}
    require(len(keyed) == len(records) and set(keyed) == expected, 'Complete unique frozen score grid required')
    require(all(np.isfinite(v) for v in keyed.values()), 'Nonfinite score')
    result = []
    for row in rows:
        require(len(row['test']) == 84, 'Exactly84 frozen test items required')
        values = []
        for item in row['test']:
            require(item['label'] in (0, 1), 'Binary frozen label required')
            sign = 1 if item['label'] == 1 else -1
            scores = {arm: sign * np.mean([keyed[row['key'], item['id'], j, arm]
                      for j in range(len(item['pairs']))]) for arm in ARMS}
            j = scores['none'] - scores['J']
            random = np.mean([scores['none'] - scores['random' + str(i)] for i in range(5)])
            pca = scores['none'] - scores['PCA']
            values.append((j, random, pca, j - random))
        result.append(np.asarray(values, dtype=np.float64))
    return result


def bootstrap(values):
    values = np.asarray(values, dtype=np.float64)
    require(values.shape == (84, 4) and np.isfinite(values).all(), 'Finite84-item four-metric matrix required')
    # Reset per row, frozen item order; one paired item draw shared by all metrics.
    indices = np.random.default_rng(SEED).integers(0, 84, size=(DRAWS, 84))
    means = values[indices].mean(axis=1)
    intervals = np.quantile(means, [.025, .975], axis=0, method='linear')
    return {name: {'estimate': float(values[:, i].mean()),
                   'ci95': [float(intervals[0, i]), float(intervals[1, i])]}
            for i, name in enumerate(METRICS)}


def main():
    require(not OUT.exists(), 'POST HOC artifact already exists; do not overwrite')
    source_verify()
    analysis = HERE / 'analysis_20261027'
    original_seal = verify(analysis, 'ANALYSIS_SEAL.json')
    sealed = read(analysis / 'RESULTS.json')
    require(original_seal['status'] == sealed['status'] == 'COMPLETE', 'Sealed registered analysis required')
    pull = CACHE / 'verified-pull-rerun1'
    receipt = read(pull / 'VERIFIED_PULL.json'); final = pull / 'final'
    require(receipt.get('issuer') == 'integrator' and receipt.get('verified_complete') is True
            and receipt.get('experiment') == 'E58b', 'Verified Integrator pull required')
    require(receipt['output_seal_sha256'] == sha(final / 'OUTPUT_SEAL.json')
            == original_seal['output_seal_sha256'] == sealed['output_seal_sha256'], 'Original output linkage mismatch')
    require(verify(final, 'OUTPUT_SEAL.json')['status'] == 'COMPLETE', 'Complete sealed raw output required')
    request = read(HERE / 'LAUNCH_REQUEST.json')
    require(sealed['request_sha256'] == sha(HERE / 'LAUNCH_REQUEST.json')
            and sealed['analysis_source_seal_sha256'] == sha(HERE / 'SOURCE_SEAL.20261027.json'),
            'Original request/source linkage mismatch')
    inp = CACHE / 'pod_inputs_v2'
    require(sha(inp / 'INPUT_SEAL.json') == sealed['input_seal_sha256'] == request['input_seal_sha256'],
            'Original input linkage mismatch')
    verify(inp, 'INPUT_SEAL.json'); pod = read(inp / 'BANK.json')
    join = load_custodied_join(request, pod, sealed['input_seal_sha256'])
    raw = [json.loads(line) for line in (final / 'scores.jsonl').read_text().splitlines()]
    rows, records = join_records(pod, join, raw)
    require(len(rows) == len(sealed['rows']) == 37, 'All37 frozen rows required')
    arrays = item_damage(rows, records)
    results = []
    for row, values, reference in zip(rows, arrays, sealed['rows']):
        require(row['key'] == reference['row'], 'Sealed row order mismatch')
        metrics = bootstrap(values)
        expected = [reference['damage']['J'], reference['random_damage_mean5'], reference['damage']['PCA'],
                    reference['damage']['J'] - reference['random_damage_mean5']]
        require(np.allclose([metrics[k]['estimate'] for k in METRICS], expected, rtol=0, atol=1e-12),
                'Post-hoc point estimates differ from sealed estimates')
        results.append({'row': row['key'], 'feature': row['feature'], 'category': row['category'],
                        'control': row['control'], 'n_items': 84, 'metrics': metrics})
    sources = [HERE / 'SOURCE_SEAL.20261027.json', HERE / 'LAUNCH_REQUEST.json',
               HERE / 'CPU_CUSTODY_BINDING.20261027.json', analysis / 'ANALYSIS_SEAL.json',
               analysis / 'RESULTS.json', analysis / 'RESULTS.md', pull / 'VERIFIED_PULL.json',
               final / 'OUTPUT_SEAL.json', final / 'scores.jsonl', inp / 'INPUT_SEAL.json', inp / 'BANK.json',
               CACHE / 'cpu_only_v2/CPU_SEAL.json', CACHE / 'cpu_only_v2/CPU_JOIN.json',
               CACHE / 'cpu_only_v2/INTEGRATOR_CUSTODY.json', Path(__file__), HERE / 'common58.py',
               HERE / 'cpu_join58.py', HERE / 'test_posthoc_ci_20261027.py']
    dump(OUT, {'experiment': 'E58b', 'label': 'POST HOC', 'status': 'COMPLETE_DESCRIPTIVE',
        'authority_commit': 'db55584a087dcd56bc151a1aaa3627e236b29440',
        'generated_utc': datetime.now(timezone.utc).isoformat(), 'CPU_only': True, 'model_calls': 0,
        'registered_analysis_rerun': False, 'sealed_verdicts_changed': False,
        'sealed_verdicts_reference_only': {'R_b1': sealed['R_b1'], 'R_b2': sealed['R_b2']},
        'bootstrap': {'draws': DRAWS, 'seed': SEED, 'rng': 'numpy.default_rng(20261027), reset per row',
            'numpy_version': np.__version__, 'unit': 'item', 'items_per_row': 84, 'rows': 37,
            'sampling': '84 items with replacement, frozen test-item order; same draw across all metrics and arms',
            'interval': '95% percentile, numpy.quantile([0.025,0.975], method=linear)',
            'within_item': 'Correct-minus-wrong log odds, equal mean over frozen candidate pairs',
            'damage': 'Paired none-minus-edited log odds per item; signed, no clipping',
            'random_damage': 'Arithmetic mean of five fixed random-seed damages within item; seeds not resampled',
            'random_seeds': list(SEEDS), 'J_minus_random': 'Paired within-item contrast before resampling',
            'scope': 'All37 frozen rows, no exclusions; no ratio intervals or rule reinterpretation'},
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sources}, 'rows': results})
    # Verify that all original artifacts remain byte-identical after CPU processing.
    require(all(sha(ROOT / name) == digest for name, digest in read(OUT)['source_sha256'].items()),
            'Source artifact changed during post-hoc computation')
    print('POST HOC artifact written:37 rows,2000 paired item draws per row; sealed verdicts unchanged.')


if __name__ == '__main__':
    main()
