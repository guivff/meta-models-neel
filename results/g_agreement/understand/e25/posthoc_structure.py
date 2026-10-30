"""2026-10-25 requested post-hoc structure correlations; registered files are read-only."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from scipy.stats import rankdata

SEED = 20261025
BOOTSTRAP = 2000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    with Path(path).open('x') as stream:
        json.dump(obj, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def rho(x, y, axis=None):
    a, b = rankdata(x, method='average', axis=axis), rankdata(y, method='average', axis=axis)
    a = a - a.mean(axis=axis, keepdims=True)
    b = b - b.mean(axis=axis, keepdims=True)
    den = np.sqrt((a*a).sum(axis=axis) * (b*b).sum(axis=axis))
    with np.errstate(invalid='ignore', divide='ignore'):
        return (a*b).sum(axis=axis) / den


def run(source, out):
    source, out = Path(source), Path(out)
    if out.exists():
        raise ValueError('Existing post-hoc output: no overwrite or implicit rerun')
    seal_path = source/'ANALYSIS_SEAL.json'
    if sha(seal_path) != '996bbf532f046a0fa249f1cf80b44b9f114138e2c95daf4ddef20e1b8ef11b27':
        raise ValueError('Wrong registered source seal')
    seal = json.loads(seal_path.read_text())
    for name, digest in seal['files'].items():
        if Path(name).name != name or sha(source/name) != digest:
            raise ValueError('Registered result changed')
    source_metrics = json.loads((source/'SUMMARY.json').read_text())
    if len(source_metrics['rows']) != 25 or source_metrics['clarifications']['D_definition'] != 'AUROC(s_A-s_B,value_is_A)':
        raise ValueError('Wrong registered row set or D')
    selected = [r for r in source_metrics['rows'] if r['class'] == 'structure']
    if len(selected) != 16 or len({r['feature'] for r in selected}) != 16:
        raise ValueError('Require all 16 distinct frozen structure rows')
    d = np.array([r['D'] for r in selected], dtype=float)
    oracle = np.array([r['W1']['olens'] for r in selected], dtype=float)
    nla = np.array([r['W1']['nla'] for r in selected], dtype=float)
    if not np.isfinite([d, oracle, nla]).all() or np.min([d, oracle, nla]) < 0 or np.max([d, oracle, nla]) > 1:
        raise ValueError('Invalid source AUROC')
    out.mkdir(parents=True, exist_ok=False)
    plan = {
        'date': datetime.now(ZoneInfo('Europe/Zurich')).isoformat(timespec='seconds'),
        'status': 'POST_HOC_DESCRIPTIVE_REQUESTED_AFTER_REGISTERED_RESULTS',
        'authority': 'User request and coordinator §119 dated note, 3928d56d',
        'source_summary_sha256': sha(source/'SUMMARY.json'),
        'registered_analysis_seal_sha256': sha(seal_path),
        'code_sha256': sha(__file__),
        'selection': 'Every frozen structure row in the full-precision sealed E25 summary; no D-based filtering',
        'row_ids': [r['feature'] for r in selected],
        'paired_difference': 'NLA asked AUROC minus Oracle asked AUROC within the same row, then Spearman versus D',
        'seed': SEED, 'bootstrap': BOOTSTRAP,
        'bootstrap_unit': '16 rows sampled with replacement; same row draws for D, both readers and their paired difference',
        'interval': 'Percentile 95%, linear quantiles; average ranks for ties; undefined draws counted, not replaced',
        'scope': 'CPU only; no registered analysis rerun, source rewrite, new model scoring or E27 work',
    }
    dump(out/'PLAN.json', plan)
    draws = np.random.default_rng(SEED).integers(0, 16, size=(BOOTSTRAP, 16))
    results = {}
    for name, outcome in [('Oracle_asked', oracle), ('NLA_asked', nla), ('NLA_minus_Oracle_asked', nla-oracle)]:
        boot = rho(d[draws], outcome[draws], axis=1)
        good = boot[np.isfinite(boot)]
        point = float(rho(d, outcome))
        results[name] = {
            'rho_with_D': point if np.isfinite(point) else None,
            'ci95': np.quantile(good, [0.025, 0.975]).tolist() if len(good) else None,
            'bootstrap_draws': BOOTSTRAP, 'finite_draws': int(len(good)),
            'undefined_draws': int(BOOTSTRAP-len(good)),
        }
    metrics = {
        'date': plan['date'], 'status': plan['status'], 'n_structure_rows': 16,
        'seed': SEED, 'bootstrap': BOOTSTRAP, 'correlations': results,
        'rows': [{'feature':r['feature'], 'D':float(d[i]), 'Oracle_asked':float(oracle[i]),
                  'NLA_asked':float(nla[i]), 'NLA_minus_Oracle_asked':float(nla[i]-oracle[i])}
                 for i,r in enumerate(selected)],
        'interpretation_limit': 'Post-hoc association among 16 row point estimates; row bootstrap omits item-level uncertainty in D and reader AUROCs. No confirmatory verdict or causal interpretation.',
        'source_summary_sha256': plan['source_summary_sha256'],
        'registered_analysis_seal_sha256': plan['registered_analysis_seal_sha256'],
        'plan_sha256': sha(out/'PLAN.json'), 'code_sha256': plan['code_sha256'],
    }
    dump(out/'METRICS.json', metrics)
    lines = ['# E25 post-hoc structure-only correlations — 2026-10-25', '',
             '**Post-hoc and descriptive**, requested after the registered results. All 16 frozen structure rows are included.', '',
             'D is the conventional fixed A-minus-B AUROC. Source values retain full precision from the sealed E25 summary.', '',
             '| Outcome correlated with D | Spearman rho | 95% row-bootstrap CI |',
             '|---|---:|---:|']
    for name, result in results.items():
        ci=result['ci95']
        value='undefined' if result['rho_with_D'] is None else f"{result['rho_with_D']:.4f}"
        interval='undefined' if ci is None else f'[{ci[0]:.4f}, {ci[1]:.4f}]'
        lines.append(f'| {name.replace("_", " ")} | {value} | {interval} |')
    lines += ['', 'The third row correlates D with the within-row difference **NLA asked AUROC minus Oracle asked AUROC**; it is not a difference between two correlation coefficients.', '',
              'Intervals use 2,000 resamples of 16 rows (seed 20261025), with the same draws preserving all within-row pairings. Average ranks handle ties. Undefined draws are counted in METRICS.json; none are replaced.', '',
              metrics['interpretation_limit'], '',
              'The registered RESULTS.md, SUMMARY.json, analysis code, scores and seals remain unchanged. No registered bootstrap, model call, GPU work, API call or E27 analysis was rerun.', '']
    with (out/'RESULTS.md').open('x') as stream:
        stream.write('\n'.join(lines))
    # Recheck the old sealed bytes after the new calculation.
    for name, digest in seal['files'].items():
        if sha(source/name) != digest:
            raise ValueError('Registered output changed during post-hoc run')
    dump(out/'SEAL.json', {'status':'POST_HOC_STRUCTURE_ANALYSIS_COMPLETE',
        'files': {name:sha(out/name) for name in ('PLAN.json','METRICS.json','RESULTS.md')},
        'registered_outputs_unchanged': True})
    print(json.dumps(results, indent=2, allow_nan=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', required=True)
    args=parser.parse_args()
    run(args.source, args.out)
