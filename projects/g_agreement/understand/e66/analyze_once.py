"""Integrator-only post-judging E66 analysis. Never reads readout text."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from common.stats import wilson

COUNTS = {'S1': 128, 'S2': 137, 'S3': 68, 'S4': 59, 'C': 150}
FIELDS = {'S1', 'S2', 'S3', 'S4', 'topic', 'eval_awareness'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def rate(values):
    k, n = sum(values), len(values)
    if not n:
        return {'k': 0, 'n': 0, 'rate': None, 'wilson95': [None, None]}
    p, lo, hi = wilson(k, n)
    return {'k': k, 'n': n, 'rate': float(p), 'wilson95': [float(lo), float(hi)]}


def analyze(judgments, mapping, *, excluded_path_ids=()):
    keys = [r['id'] for r in judgments]
    mids = [r['id'] for r in mapping]
    if len(keys) != 542 or len(set(keys)) != 542 or len(set(mids)) != 542 or len(mids) != 542 or set(keys) != set(mids):
        raise ValueError('Incomplete, duplicate, or mismatched IDs')
    if Counter(r['stratum'] for r in mapping) != COUNTS:
        raise ValueError('Achieved stratum counts differ from sealed sample')
    normalized, excluded = [], []
    for row in judgments:
        if row.get('status') == 'UNPARSEABLE':
            if row.get('code') is not None:
                raise ValueError('UNPARSEABLE must not carry a scored code')
            excluded.append(row['id'])
            continue
        if 'status' in row:
            if row['status'] != 'KEPT' or not isinstance(row.get('code'), dict):
                raise ValueError('Only terminal KEPT or UNPARSEABLE records accepted')
            r = row['code']
            if r.get('id') != row['id']:
                raise ValueError('Envelope/code ID mismatch')
        else:
            r = row
        if set(r) not in (FIELDS | {'id'}, FIELDS | {'id', 'evidence'}) or any(type(r[f]) is not bool for f in FIELDS):
            raise ValueError('Judgments require six strict boolean codes and id')
        if 'evidence' in r and (not isinstance(r['evidence'], dict) or set(r['evidence']) != FIELDS or any(not isinstance(v, str) for v in r['evidence'].values())):
            raise ValueError('Evidence must contain six string fields')
        # Evidence has already been validated by the blind judge runner; never
        # inspect readouts or reproduce evidence text in analysis output.
        normalized.append({f: r[f] for f in FIELDS | {'id'}})
    omitted = set(excluded_path_ids)
    if not omitted <= set(keys):
        raise ValueError('Unknown path-redacted ID')
    normalized = [r for r in normalized if r['id'] not in omitted]
    excluded = [i for i in excluded if i not in omitted]
    judgments = normalized
    strata = {r['id']: r['stratum'] for r in mapping}
    groups = {s: [r for r in judgments if strata[r['id']] == s] for s in COUNTS}
    structural = rate([r[strata[r['id']]] for r in judgments if strata[r['id']] != 'C'])
    topic_c = rate([r['topic'] for r in groups['C']])
    evaluable = structural['n'] > 0 and topic_c['n'] > 0
    holds = evaluable and structural['rate'] <= .05 and structural['wilson95'][1] <= .10 and topic_c['rate'] >= .50
    falsified = structural['n'] > 0 and structural['rate'] >= .20
    return {'judgment_accounting': {'total': 542-len(omitted), 'path_redacted_excluded': len(omitted), 'kept': len(judgments),
                'UNPARSEABLE': len(excluded), 'flag': bool(excluded),
                'excluded_ids': sorted(excluded),
                'excluded_by_stratum': {s: sum(strata[i] == s for i in excluded) for s in COUNTS},
                'policy': 'UNPARSEABLE records excluded from all rates; no replacement'},
            'R_G1': {'verdict': 'HOLDS' if holds else 'FALSIFIED' if falsified else 'INCONCLUSIVE' if evaluable else 'NOT_EVALUABLE',
                      'holds': holds, 'falsifier': falsified, 'pooled_structural': structural, 'C_topic': topic_c},
            'R_G2': {s: {'structural': rate([r[s] for r in rows]) if s != 'C' else None,
                           'topic': rate([r['topic'] for r in rows])} for s, rows in groups.items()},
            'R_G3': {'reporting': 'UNSTRATIFIED', 'eval_awareness': rate([r['eval_awareness'] for r in judgments])},
            'shortfalls_vs_150': {s: 150-n for s, n in COUNTS.items()},
            'caveat': 'Text-derived structure is not verified as represented in GLM; a miss does not establish absent state.'}


def analyze_views(judgments, mapping, redacted_ids):
    if (not isinstance(redacted_ids, list) or len(redacted_ids) != 3
            or any(not isinstance(i, str) for i in redacted_ids)
            or len(set(redacted_ids)) != 3
            or not set(redacted_ids) <= {r['id'] for r in judgments}):
        raise ValueError('Require exactly three distinct packet IDs from integrator')
    return {'all_records': analyze(judgments, mapping),
            'excluding_path_redacted': analyze(judgments, mapping, excluded_path_ids=redacted_ids),
            'sensitivity': {'authority': '79f63fe0', 'excluded_ids': sorted(redacted_ids),
                           'primary_n': 542, 'sensitivity_n': 539,
                           'note': 'UNPARSEABLE excluded from rates separately in each view; thresholds unchanged.'}}


def run(spec_path):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    root = Path(spec['repo_root']).resolve()
    seal = json.loads(spec_path.with_name('ANALYSIS_COMMAND_SEAL.json').read_text())
    for rel, digest in seal['files'].items():
        if sha(root / rel) != digest:
            raise ValueError('Analysis command hash mismatch')
    out = Path(spec['output']).resolve()
    out.relative_to(root / 'cache')
    out.mkdir(parents=True, exist_ok=True)
    # Exclusive persistent lock: failed attempts are retained, never automatically retried.
    with (out / 'INVOKED_ONCE.lock').open('x') as f:
        f.write('Integrator-only invocation; retain on success or failure.\n')
    try:
        js = json.loads(Path(spec['judgment_seal']).read_text())
        if js['status'] != 'SEALED_BLIND_JUDGMENTS' or js['n'] != 542 or js['packet_sha256'] != spec['packet_sha256'] or js['strata_joined'] is not False:
            raise ValueError('Blind judgment completion seal required before join')
        if sha(spec['judgments']) != js['judgments_sha256']:
            raise ValueError('Judgment digest mismatch')
        if sha(spec['rubric']) != js['rubric_sha256']:
            raise ValueError('Frozen rubric digest mismatch')
        if sha(spec['redacted_ids']) != js['redacted_ids_sha256']:
            raise ValueError('Path-redacted ID digest mismatch')
        redacted_ids = json.loads(Path(spec['redacted_ids']).read_text())
        judgments = [json.loads(line) for line in Path(spec['judgments']).read_text().splitlines()]
        # No map is opened until completed blind judgments and frozen rubric are verified.
        if sha(spec['private_map']) != spec['private_map_sha256']:
            raise ValueError('Private map digest mismatch')
        mapping = [json.loads(line) for line in Path(spec['private_map']).read_text().splitlines()]
        result = analyze_views(judgments, mapping, redacted_ids)
        result.update(status='SEALED', judgment_seal_sha256=sha(spec['judgment_seal']),
                      command_seal_sha256=sha(spec_path.with_name('ANALYSIS_COMMAND_SEAL.json')))
        write(out / 'RESULTS.json', result)
        write(out / 'ANALYSIS_SEAL.json', {'status': 'SEALED', 'results_sha256': sha(out / 'RESULTS.json'),
              'judgments_sha256': js['judgments_sha256'], 'redacted_ids_sha256': js['redacted_ids_sha256'], 'private_map_sha256': spec['private_map_sha256']})
    except Exception:
        write(out / 'INVALID.json', {'status': 'INVALID', 'instruction': 'Retain lock; no replacement, rerun or denominator change without coordinator direction.'})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--integrator-post-judging', action='store_true', required=True)
    args = parser.parse_args()
    run(args.spec)


if __name__ == '__main__':
    main()
