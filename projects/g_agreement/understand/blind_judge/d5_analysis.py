"""Sealed CPU-only E49 D5 aggregation. No judge/model calls; integrator runs once."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from projects.g_agreement.readerbench.io import read, sha, verify, seal_output
from projects.g_agreement.readerbench.scoring import D5, require

ROOT = Path(__file__).resolve().parents[4]
HERE = ROOT/'results/g_agreement/understand/e61/d5'


def exclusive(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def join_grid(keys, terminal, inventory):
    selected = [x for x in terminal if x['job'] == 'D5_E49']
    km = {x['opaque_id']: x for x in keys}
    require(len(km) == len(keys) == len(selected) and
            len({x['id'] for x in selected}) == len(selected) and
            {x['id'] for x in selected} == set(km), 'exact D5 judgment/key grid')
    rows = []
    for x in selected:
        k = km[x['id']]
        require(x['status'] in ('KEPT', 'UNPARSEABLE') and
                type(x['attempts']) is int and 0 <= x['attempts'] <= 2, 'terminal status/attempts')
        if x['status'] == 'UNPARSEABLE':
            require(x['code'] is None and x['attempts'] == 2, 'unresolved exhausted retry')
            category = None
        else:
            require(x['code']['id'] == x['id'] and x['code']['category'] in D5, 'frozen D5 code')
            category = x['code']['category']
        rows.append(dict(bank=k['bank'], row=k['row'], item_id=k['item_id'],
                         category=category, attempts=x['attempts']))
    actual = defaultdict(list)
    for r in rows:
        actual[r['bank'], r['row']].append(r)
    expected = {(x['bank'], x['row']): x for x in inventory['rows']}
    require(set(actual) == set(expected), 'exact sealed row scope')
    for key, group in actual.items():
        i = expected[key]
        require(len(group) == i['n_readouts'] and
                {r['item_id'] for r in group} == set(i['source_ids']) and
                len({r['item_id'] for r in group}) == i['n_items'], 'sealed item/repeat inventory')
    return rows


def proportions(counts):
    counts = np.asarray(counts, dtype=float)
    denominator = counts.sum(axis=-1, keepdims=True)
    return np.divide(counts, denominator, out=np.full_like(counts, np.nan), where=denominator > 0)


def describe_shares(point, draws):
    result = {}
    for j, category in enumerate(D5):
        valid = draws[:, j][np.isfinite(draws[:, j])]
        result[category] = dict(share=float(point[j]) if np.isfinite(point[j]) else None,
            ci95=np.quantile(valid, [.025, .975]).tolist() if len(valid) else None,
            defined_draws=len(valid), undefined_draws=len(draws)-len(valid))
    return result


def missingness(records):
    n = len(records); u = sum(x['category'] is None for x in records)
    return dict(n_readouts=n, kept=n-u, unparseable=u, unparseable_rate=u/n,
                flagged_over_5_percent=20*u > n,
                retried=sum(x['attempts'] > 0 for x in records),
                retry_requests=sum(x['attempts'] for x in records))


def aggregate(records, draws=2000, seed=20261027):
    require(records and draws > 0, 'nonempty aggregation')
    groups = defaultdict(list)
    for r in records:
        require(r['category'] is None or r['category'] in D5, 'D5 taxonomy')
        groups[r['bank'], r['row']].append(r)
    rng = np.random.default_rng(seed)
    report = []; boot_counts = []; points = []
    for (bank, row), group in sorted(groups.items()):
        clusters = defaultdict(lambda: np.zeros(5, dtype=int))
        for r in group:
            counts = clusters[r['item_id']]  # include wholly UNPARSEABLE clusters
            if r['category'] is not None:
                counts[D5.index(r['category'])] += 1
        matrix = np.array([clusters[k] for k in sorted(clusters)])
        sampled = np.empty((draws, 5), dtype=int)
        for start in range(0, draws, 100):
            ix = rng.integers(len(matrix), size=(min(100, draws-start), len(matrix)))
            sampled[start:start+len(ix)] = matrix[ix].sum(axis=1)
        point = matrix.sum(axis=0)
        points.append(point);boot_counts.append(sampled)
        report.append(dict(bank=bank, row=row, n_items=len(matrix), **missingness(group),
            counts=dict(zip(D5, map(int, point))),
            categories=describe_shares(proportions(point), proportions(sampled))))
    weighted = describe_shares(proportions(np.sum(points, axis=0)),
                               proportions(np.sum(boot_counts, axis=0)))
    equal = describe_shares(np.mean(proportions(points), axis=0),
                            np.mean(proportions(boot_counts), axis=0))
    return dict(descriptive_only=True, scope='E49 tranche only', rows=report,
        pooled=dict(**missingness(records), n_rows=len(report),
                    counts=dict(zip(D5, map(int, np.sum(points, axis=0)))),
                    readout_weighted=weighted, equal_row=equal),
        bootstrap=dict(draws=draws, seed=seed, interval='percentile95',
                       unit='item cluster within fixed bank/row; all repeats and missingness retained'))


def preflight():
    source = read(HERE/'ANALYSIS_SOURCE_SEAL.json')
    for name, digest in source['files'].items():
        require(sha(ROOT/name) == digest, 'D5 source changed: '+name)
    spec = read(HERE/'ANALYSIS_COMMAND.json')
    for name, digest in spec['files'].items():
        require(sha(name) == digest, 'D5 input changed: '+name)
    for path, digest in spec['seals'].items():
        verify(path, digest)
    return spec


def run(spec):
    require(not (ROOT/spec['guard']).exists() and not (ROOT/spec['out']).exists(), 'D5 already attempted')
    inventory = read(spec['inventory'])
    terminal = read(spec['terminal'])
    keys = read(spec['key'])
    records = join_grid(keys, terminal, inventory)
    require(len(records) == 504, 'frozen 504-readout E49 scope')
    # Atomic and shared with the original prepared D5 runner. Never remove on failure.
    exclusive(ROOT/spec['guard'], dict(authority='965e4baa',
        source_seal_sha256=sha(HERE/'ANALYSIS_SOURCE_SEAL.json'),
        command_sha256=sha(HERE/'ANALYSIS_COMMAND.json')))
    out = ROOT/spec['out'];out.mkdir(parents=True, exist_ok=False)
    try:
        result = aggregate(records)
        result['pending_bank_adjudications'] = inventory['pending_bank_adjudications']
        exclusive(out/'RESULTS.json', result)
        seal_output(out, dict(status='COMPLETE_ONCE', authority='965e4baa',
            source_seal_sha256=sha(HERE/'ANALYSIS_SOURCE_SEAL.json'),
            command_sha256=sha(HERE/'ANALYSIS_COMMAND.json'),
            terminal_seal_sha256=spec['terminal_seal_sha256']))
    except Exception as exc:
        exclusive(out/'FAILED.json', dict(error=str(exc), retry=False))
        raise


if __name__ == '__main__':
    run(preflight())
