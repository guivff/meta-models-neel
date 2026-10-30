"""E63 once-only CPU regex coding; R-P2 waits for sealed blind judgments."""
import argparse
from pathlib import Path
from collections import Counter
from .io import load_bundle, write, seal_output, verify_sources
from .score_reader import score
from .scoring import require


def validate_scope(data):
    require(data.get('scope_complete') is True, 'complete frozen E63 row inventory required')
    require(data.get('banks') == ['E56', 'E57', 'E59', 'E62'], 'all registered banks required')
    keys = [(r['bank'], r['row'], r['reader']) for r in data['rows']]
    require(len(keys) == len(set(keys)) and sorted(map(list, keys)) == sorted(data['expected_rows']),
            'frozen real-row inventory mismatch')
    require({r['reader'] for r in data['rows']} == {'oracle', 'nla'}, 'both readers required')
    pools = data['placebo']
    require(len({r['id'] for r in pools}) == len(pools), 'duplicate placebo IDs')
    require({(r['reader'], r['arm']) for r in pools} ==
            {(r, a) for r in ('oracle', 'nla') for a in ('random', 'shuffled')}, 'pool arms')
    for reader in ('oracle', 'nla'):
        for arm in ('random', 'shuffled'):
            xs = [r for r in pools if r['reader'] == reader and r['arm'] == arm]
            counts = Counter(r['item_id'] for r in xs)
            require(len(counts) == 200 and set(counts.values()) == {4}, '200 vectors * 4 repeats')
            require(all(r['layer'] == (44 if reader == 'oracle' else 42) for r in xs), 'native layer')
            require(len({(r['item_id'], r['repeat']) for r in xs}) == 800 and
                    {r['repeat'] for r in xs} == {0, 1, 2, 3}, 'repeat grid')
    for row in data['rows']:
        require(row['bank'] in data['banks'], 'out-of-scope row')
        require(sorted(r['id'] for r in row['readouts']) == sorted(row['expected_readout_ids']),
                'full real readout grid required')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle-seal', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    verify_sources()
    data, receipt = load_bundle(a.bundle_seal, a.sha256)
    validate_scope(data)
    # Fixed experiment guard, never scoped to an arbitrary output path.
    root = Path(__file__).resolve().parents[3]
    guard = root/'cache/g_agreement/understand/e63/REGEX_ANALYSIS_ONCE.json'
    guard.parent.mkdir(parents=True, exist_ok=True)
    require(not a.out.exists(), 'output exists')
    with guard.open('x') as f:
        f.write(a.sha256+'\n')
    try:
        result = {reader: score(data, reader) for reader in ('oracle', 'nla')}
        a.out.mkdir(parents=True, exist_ok=False)
        write(a.out/'REGEX_RESULTS.json', result)
        write(a.out/'R_P2_STATUS.json', {'status': 'PENDING_SEALED_JUDGMENTS',
                                     'NLA_reference': 'matching-reader MISSED distribution required; never substitute Oracle'})
        seal_output(a.out, {'experiment': 'E63', 'status': 'REGEX_COMPLETE_ONCE',
                            'input_seal_sha256': a.sha256})
    except Exception as exc:
        write(guard.with_name('REGEX_FAILURE.json'), {'error_type': type(exc).__name__,
                                                     'input_seal_sha256': a.sha256})
        raise


if __name__ == '__main__':
    main()
