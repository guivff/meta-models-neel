"""Once-only aggregation of complete sealed blind grids; no judge implementation."""
import argparse
from pathlib import Path
from .io import load_bundle, read, sha, write, seal_output, verify_sources
from .scoring import require, validate_judgments, category_shares, placebo_tvd, RUBRIC_HASHES


def join_grid(data, job):
    route = data['route']
    require(route.get('assigned') is True and route.get('route_id') and route.get('configuration'),
            'actual integrator-assigned E56 judge route required')
    require(route == data['E56_route'], 'judge route differs from E56')
    taxonomy = 'E56' if job == 'E54' else 'D5'
    judgments = validate_judgments(data['packet'], data['judgments'], taxonomy)
    keys = data['private_key']
    require(len(keys) == len(judgments) and {x['opaque_id'] for x in keys} == set(judgments),
            'private key must cover the complete blind grid exactly once')
    if job == 'E54':
        require(len(keys) == 336, 'E54 complete grid required')
    if job == 'D5':
        require(data.get('scope_complete') is True, 'D5 full inventory not closed')
    # All judgments validated before joining any labels.
    return [dict(k, category=judgments[k['opaque_id']]['category'],
                 values=judgments[k['opaque_id']].get('values'),
                 evidence=judgments[k['opaque_id']]['evidence']) for k in keys]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job', choices=['E54', 'D5', 'E63_RP2'], required=True)
    p.add_argument('--bundle-seal', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    verify_sources()
    data, receipt = load_bundle(a.bundle_seal, a.sha256)
    require({'packet', 'judgments', 'route', 'E56_route', 'private_key', 'rubric'} <=
            set(data['sealed_components']), 'separate pre-join component seals required')
    for name, binding in data['sealed_components'].items():
        require(sha(binding['path']) == binding['sha256'], 'component seal mismatch')
        # The sealed bundle also carries exact component contents; reject substituted copies.
        if name != 'rubric':
            require(read(binding['path']) == data[name], 'component payload mismatch')
    require(data['sealed_components']['rubric']['sha256'] ==
            RUBRIC_HASHES['E56' if a.job == 'E54' else 'D5'], 'registered rubric mismatch')
    rows = join_grid(data, a.job)
    if a.job == 'E63_RP2':
        require('missed_categories' in data['sealed_components'], 'sealed MISSED reference required')
        require(all(data['missed_categories'].get(r) for r in ('oracle', 'nla')),
                'matching-reader MISSED distributions required; no cross-reader substitution')
    root = Path(__file__).resolve().parents[3]
    guard = root/'cache/g_agreement/understand/blind_coding'/f'{a.job}_ANALYSIS_ONCE.json'
    guard.parent.mkdir(parents=True, exist_ok=True)
    require(not a.out.exists(), 'output exists')
    with guard.open('x') as f:
        f.write(a.sha256+'\n')
    try:
        if a.job == 'D5':
            result = category_shares(rows)
        elif a.job == 'E54':
            # Lossless export for the integrator, including both-value assertions.
            result = {'status': 'COMPLETE_BLIND_CODING', 'judgments': rows,
                      'note': 'E5354 old single-value context needs a lossless adapter before analysis.'}
        else:
            result = {}
            for reader in ('oracle', 'nla'):
                xs = [r['category'] for r in rows if r['reader'] == reader]
                require(len(xs) == 200, 'R-P2 requires 200 readouts per reader')
                missed = data['missed_categories'].get(reader)
                result[reader] = placebo_tvd(xs, missed)
        a.out.mkdir(parents=True, exist_ok=False)
        write(a.out/'RESULTS.json', result)
        seal_output(a.out, {'job': a.job, 'status': 'COMPLETE_ONCE', 'input_seal_sha256': a.sha256})
    except Exception as exc:
        write(guard.with_suffix('.failure.json'), {'error_type': type(exc).__name__})
        raise


if __name__ == '__main__':
    main()
