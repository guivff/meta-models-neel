"""Prepare the verified E49 tranche; do not close the all-bank D5 inventory or judge."""
import argparse
import json
from pathlib import Path
from .io import read, write, sha, verify, seal_output
from .blind import packet
from .scoring import require

ANALYSIS = 'd5475983c6ee5796c74436f9c86cfdebcdd4f65557ab4f1804627a2c3dd7d044'
OUTPUT = 'b1219929c22dcf1f0af7cf31b41ad873cc21c99c48efbaa567511d5f284b9e86'
BANK = 'ccc2b3b6e27d0227f2d17f1de0efe2cb9a33cfd4d299656f19d7e4a4e3db43c9'
QUESTIONS = {
    'asserted_vs_hypothetical': 'Whether the statement is asserted or hypothetical',
    'branch_taken': 'Whether the conditional branch is taken',
    'container_after_move': 'The current container after the move',
    'unit_system': 'The measurement unit system',
    'user_expertise': 'The user expertise register',
    'var_type_at_use': 'The variable type at its current use',
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, required=True)
    a = p.parse_args()
    own = Path(__file__).resolve().parents[3]
    mech = a.workspace/'wt-wmech'
    analysis = mech/'results/g_agreement/understand/e49/job/analysis'
    pull = mech/'cache/g_agreement/understand/e49/verified_section149'
    bank = a.workspace/'wt-wtext/results/g_agreement/understand/e49/cache/frozen_2026-10-26'
    s = verify(analysis/'ANALYSIS_SEAL.json', ANALYSIS)
    output = verify(pull/'out/OUTPUT_SEAL.json', OUTPUT)
    require(s['status'] == 'COMPLETE_ONCE' and output['status'] == 'COMPLETE', 'complete E49 required')
    require(s['output_seal_sha256'] == OUTPUT, 'analysis output binding')
    receipt = read(pull/'INTEGRATOR_VERIFIED.json')
    require(receipt['verified'] is True and receipt['experiment'] == 'E49' and
            receipt['output_seal_sha256'] == OUTPUT and receipt['source_seal_sha256'] == s['source_seal_sha256'],
            'integrator custody binding')
    verify(mech/'results/g_agreement/understand/e49/job/SOURCE_SEAL.json', s['source_seal_sha256'])
    verify(bank/'BANK_SEAL.json', BANK)
    native = read(analysis/'NATIVE_PRIMARY.json')
    selected = sorted(k for k in native['qualified_rows'] if native['rows'][k]['oracle']['forecast_truth'] == 'MISSED')
    require(set(selected) == set(QUESTIONS), 'scope changed; stop and review inventory')
    items = read(bank/'items.PRIVATE.json')
    records, inventory = [], []
    for row in selected:
        tests = {x['id']: x for x in items if x['feature'] == row and x['split'] == 'test'}
        values = {}
        for label in (0, 1):
            vs = {x['value'] for x in tests.values() if x['label'] == label}
            require(len(vs) == 1, 'ambiguous value definition')
            values[('A', 'B')[label]] = vs.pop()
        path = pull/'out/readers'/row/'oracle_native.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        require(len(rows) == native['rows'][row]['oracle']['n'] == 84 and
                {x['id'] for x in rows} == set(tests), 'all acquired native test readouts required')
        inventory.append({'bank': 'E49', 'row': row, 'n_readouts': len(rows),
                          'n_items': len(tests), 'native_file_sha256': sha(path),
                          'source_ids': [x['id'] for x in rows], 'acquired_repeats_per_item': 1})
        for x in rows:
            require(x['block'] == 44 and x['feature'] == row, 'native channel')
            records.append({'id': x['id'], 'item_id': x['id'], 'reader': 'oracle', 'bank': 'E49',
                            'row': row, 'native_status': 'MISSED', 'text': x['text'],
                            'property': QUESTIONS[row], 'values': values})
    dest = own/'cache/g_agreement/understand/e61/d5/e49_tranche'
    require(not dest.exists(), 'E49 tranche already prepared; do not duplicate')
    dest.mkdir(parents=True)
    # Freeze inventory before opaque packet generation. No judge calls occur here.
    write(dest/'INVENTORY.json', {'rows': inventory, 'scope_complete': False,
        'pending_bank_adjudications': ['W1', 'E36', 'W12', 'E56', 'E57', 'E59', 'E62'],
        'E49_excluded': native['excluded_rows'], 'analysis_seal_sha256': ANALYSIS,
        'output_seal_sha256': OUTPUT, 'integrator_receipt_sha256': sha(pull/'INTEGRATOR_VERIFIED.json')})
    public, key = packet(records)
    write(dest/'PRIVATE_KEY.json', key)
    (dest/'PRIVATE_KEY.json').chmod(0o600)
    share = dest/'public'
    share.mkdir()
    write(share/'JUDGE_PACKET.json', public)
    rubric = own/'results/g_agreement/understand/e61/d5/JUDGE_RUBRIC.md'
    (share/'JUDGE_RUBRIC.md').write_bytes(rubric.read_bytes())
    seal_output(share, {'status': 'PREPARED_NOT_JUDGED', 'scope': 'E49 tranche only',
                       'inventory_sha256': sha(dest/'INVENTORY.json'),
                       'private_key_sha256': sha(dest/'PRIVATE_KEY.json'), 'n': len(records)})
    summary = {'status': 'E49_TRANCHE_PREPARED_AWAITING_ROUTE_AND_ALL_BANK_SCOPE',
               'analysis_seal_sha256': ANALYSIS, 'output_seal_sha256': OUTPUT,
               'inventory_sha256': sha(dest/'INVENTORY.json'), 'packet_seal_sha256': sha(share/'RESULT_SEAL.json'),
               'n_readouts': len(records), 'n_rows': len(selected), 'rows': selected,
               'judge_calls': 0, 'analysis_runs': 0, 'scope_complete': False,
               'packet': 'cache/g_agreement/understand/e61/d5/e49_tranche/public',
               'note': 'One acquired native readout per item; no fabricated repeats. Other-bank scope awaits authoritative adjudication.'}
    write(own/'results/g_agreement/understand/e61/d5/E49_TRANCHE_PREPARATION.json', summary)
    print(json.dumps({'status': summary['status'], 'n_readouts': len(records), 'n_rows': len(selected)}))


if __name__ == '__main__':
    main()
