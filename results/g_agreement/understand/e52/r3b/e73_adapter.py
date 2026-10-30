"""E73 operational adapter: 400 balanced tests/state; unchanged sealed J kernel."""
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / 'results/g_agreement/understand/e57/jlens'))
import cpu_job
import forecast_once


def validate_units(units, records, order):
    # E73 is 400 tests/state, not the synthetic banks' 84. A=1/B=0 is
    # explicitly normalized by the binder, keeping the G3/mean orientation.
    if {u['id'] for u in units} != {'W1', 'W2', 'W3', 'W4', 'W5'} or len(units) != 5:
        raise ValueError('All five retained E73 states required, including probe-failing states')
    tests = {r['id']: r for r in records if r['split'] == 'test'}
    if len(tests) != 2000 or len(records) != 2000 or len(order) != 2000 or set(order) != set(tests):
        raise ValueError('Exactly all 2000 unique test positions required')
    seen = set()
    for u in units:
        ids = u['item_ids']
        if len(ids) != 400 or len(set(ids)) != 400 or seen.intersection(ids) or not set(ids) <= set(tests):
            raise ValueError('Exactly 400 unique disjoint tests per state')
        if u['source_row'] != u['id'] or u['binary'] is not True:
            raise ValueError('E73 state identity/binary mismatch')
        if set(u['value_token_ids']) != set(ids) or set(u['descriptive_token_sets']) != set(ids):
            raise ValueError('Exact frozen per-item token coverage required')
        for i in ids:
            r = tests[i]
            if r['feature'] != u['id'] or r['original_label'] not in (0, 1) or r['label'] != 1-r['original_label']:
                raise ValueError('Explicit A=0 to A=1 orientation required')
            if len(u['value_token_ids'][i]) != 2 or u['descriptive_token_sets'][i] != {}:
                raise ValueError('Exactly frozen A/B sets; no descriptive additions')
        if sum(tests[i]['label'] for i in ids) != 200:
            raise ValueError('Balanced 200 A and 200 B required')
        seen.update(ids)
    if seen != set(tests):
        raise ValueError('Omitted tests')
    return tests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['channel', 'forecast'])
    args = parser.parse_args()
    cpu_job.verify(ROOT, cpu_job.read(HERE / 'E73_ADAPTER_SEAL.json')['files'])
    cpu_job.verify(ROOT, cpu_job.read(HERE / 'CODE_SEAL_2026-10-27.json')['files'])
    cpu_job.committed(Path(__file__))
    cpu_job.validate_units = validate_units
    forecast_once.validate_units = validate_units
    return cpu_job.run('E73') if args.stage == 'channel' else forecast_once.run('E73')


if __name__ == '__main__':
    raise SystemExit(main())
