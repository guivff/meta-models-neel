"""Build public E95 inputs for the existing sealed worker; no launch operations."""
import argparse
import hashlib
import importlib
import json
import sys
import tarfile
from pathlib import Path


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def package(root, runner, row_indices, out):
    inventory = read(root/'results/g_agreement/understand/e95/ROW_INVENTORY.json')
    norms_file = root/'results/g_agreement/understand/e95/NLA_NORMS.json'
    norm_receipt = root/'results/g_agreement/understand/e95/NLA_NORM_RECEIPT.json'
    norms = read(norms_file)
    assert read(norm_receipt)['files'][norms_file.name] == sha(norms_file)
    assert row_indices == sorted(set(row_indices)) and row_indices
    source_rows = inventory['rows']
    assert set(row_indices) <= set(range(len(source_rows)))
    reuse = {source_rows[i]['reuse_e87'] for i in row_indices}
    assert len(reuse) == 1, 'E87 reuse and remaining work use separate worker modes'
    roster = []
    for row in source_rows:
        assert len(set(row['nla_position_counts'])) == 1, 'Mixed positions require explicit matching'
        roster.append(dict(row_index=row['row_index'], test_count=row['test_count'],
            item_ids=row['item_ids'], nla_norm=norms['banks'][row['bank']]['median_norm'],
            nla_norm_seal_sha256=sha(norm_receipt),
            placebo_positions=[row['nla_position_counts'][0]]*15, reuse_e87=row['reuse_e87']))
    selected = set(row_indices)
    items = [x for x in read(root/'cache/g_agreement/e95/public_items.json')
             if x['global_index']//30 in selected]
    shard = 'e95-'+('nla-placebo-' if True in reuse else 'remaining-')+'-'.join(map(str,row_indices))
    plan = dict(experiment='E95', shard=shard, layers=[20,36,44,56], oracle_positions=8,
        nla_positions=8, seed=20261029, short_positions='available', nla_placebo=True,
        reduction_step=0, scope_authority='1b0a2fcfc50d8d57d97a2f3cd84f8f88ca4e4a85',
        row_roster=roster, row_indices=row_indices,
        mode='nla_placebo_only' if True in reuse else 'remaining', item_ids=[x['id'] for x in items])
    # Use the packaged owner validation, without invoking a backend or main().
    sys.path.insert(0, str(runner/'results/g_agreement/understand/e87'))
    sys.path.insert(0, str(runner/'results/g_agreement/understand/late198'))
    worker = importlib.import_module('worker87')
    worker.validate(items, plan)
    request = dict(experiment='E95', status='HOLD_MEASURED_ADMISSION',
        cap_seconds=None, cumulative_cap_seconds=None, account_gate_USD=1500,
        seed_seconds_per_batch=None,
        pending='Operator must bind measured phase timings, allocated cap and global liabilities before READY',
        aggregate_remaining_gpu_hours_cap=40)
    out.mkdir(parents=True, exist_ok=False)
    for name, value in [('PLAN.json', plan), ('items.json', items), ('STAGE_REQUEST.json', request)]:
        (out/name).write_text(json.dumps(value, indent=2)+'\n')
    seal = dict(experiment='E95', synthetic=False,
        first_output_utc='unknown', first_output_evidence=None,
        provenance_note='Input preparation only; no readout, judgment or scientific analysis output',
        files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    (out/'INPUT_SEAL.json').write_text(json.dumps(seal, indent=2)+'\n')
    worker.verify(out, 'INPUT_SEAL.json', sha(out/'INPUT_SEAL.json'))
    assert set(p.name for p in out.iterdir()) == {'PLAN.json','items.json','STAGE_REQUEST.json','INPUT_SEAL.json'}
    archive = out.with_suffix('.tar.gz')
    with tarfile.open(archive, 'w:gz') as tar:
        for p in sorted(out.iterdir()):
            tar.add(p, arcname=p.name)
    assert archive.stat().st_size <= 20*1024*1024
    return dict(shard=shard, mode=plan['mode'], row_indices=row_indices,
        real_input_count=len(items), archive_sha256=sha(archive),
        archive_bytes=archive.stat().st_size, input_seal_sha256=sha(out/'INPUT_SEAL.json'),
        status=request['status'], GPU_calls=0, judge_calls=0)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path.cwd())
    p.add_argument('--runner', type=Path, required=True)
    p.add_argument('--row-indices', type=int, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(package(a.root,a.runner,a.row_indices,a.out)))
