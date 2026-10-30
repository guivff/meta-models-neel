"""Blind packet preparation only. Integrator assigns the actual E56 judge route."""
import argparse
import secrets
from pathlib import Path
import numpy as np
from .io import load_bundle, write, sha, seal_output, verify_sources
from .scoring import require, RUBRIC_HASHES


def packet(records, seed=20261027):
    require(len({r['id'] for r in records}) == len(records), 'duplicate source IDs')
    rng = np.random.default_rng(seed)
    public, key = [], []
    for i in rng.permutation(len(records)):
        r = records[int(i)]
        ident = secrets.token_hex(16)
        public.append({'id': ident, 'property': r['property'], 'values': r['values'],
                       'readout': r['text']})
        key.append(dict(r, opaque_id=ident))
    return public, key


def select_placebo(records):
    selected = []
    for reader in ('oracle', 'nla'):
        pool = sorted((r for r in records if r['reader'] == reader), key=lambda x: x['id'])
        require(len(pool) == 1600, 'expected two arms * 200 vectors * 4 repeats per reader')
        rng = np.random.default_rng(20261027)
        selected.extend(pool[int(i)] for i in rng.choice(len(pool), 200, replace=False))
    # D5 does not need a target row for placebo; do not invent a true value/property.
    return [dict(r, property='What this readout explicitly describes', values={}) for r in selected]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job', choices=['E54', 'E63_RP2', 'D5'], required=True)
    p.add_argument('--bundle-seal', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--rubric', type=Path, required=True)
    p.add_argument('--rubric-sha256', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--private-key', type=Path, required=True)
    a = p.parse_args()
    verify_sources()
    require(a.rubric_sha256 == RUBRIC_HASHES['E56' if a.job == 'E54' else 'D5'],
            'registered rubric required; no substitute')
    require(sha(a.rubric) == a.rubric_sha256, 'rubric mismatch')
    data, receipt = load_bundle(a.bundle_seal, a.sha256)
    records = data['records']
    if a.job == 'E54':
        require(len(records) == 336, 'E54 complete 336-readout export required')
        require(len({(r['reader'], r['item_id']) for r in records}) == 336, 'E54 duplicate units')
        require({r['row'] for r in records} == {'reasoning_bridge', 'injection_awareness'}, 'E54 rows')
        require(all(sum(r['reader'] == x for r in records) == 168 for x in ('oracle', 'nla')), 'E54 readers')
    elif a.job == 'E63_RP2':
        records = select_placebo(records)
    else:
        require(data.get('E49_analysis_verified') is True and data.get('scope_complete') is True,
                'D5 trigger and full inventory required')
        require(all(r['native_status'] == 'MISSED' and r['reader'] == 'oracle' for r in records),
                'D5 authoritative MISSED scope only')
    # Ensure private joining key is inside ignored cache, outside the shareable packet.
    import subprocess
    require(subprocess.run(['git', 'check-ignore', '-q', str(a.private_key)]).returncode == 0,
            'private key must be git-ignored')
    require(not a.private_key.resolve().is_relative_to(a.out.resolve()), 'private key must be separate')
    require(not a.private_key.exists() and not a.out.exists(), 'packet already exists')
    public, key = packet(records)
    a.out.mkdir(parents=True, exist_ok=False)
    a.private_key.parent.mkdir(parents=True, exist_ok=True)
    with a.private_key.open('x') as f:
        import json
        json.dump(key, f)
    a.private_key.chmod(0o600)
    write(a.out/'JUDGE_PACKET.json', public)
    (a.out/'JUDGE_RUBRIC.md').write_bytes(a.rubric.read_bytes())
    # This is preparation, not an assertion that a judge route is assigned or run.
    seal_output(a.out, {'job': a.job, 'status': 'AWAITING_SEALED_E56_ROUTE_AND_JUDGMENTS',
                        'n': len(public), 'input_seal_sha256': a.sha256,
                        'private_key_sha256': sha(a.private_key), 'rubric_sha256': a.rubric_sha256})


if __name__ == '__main__':
    main()
