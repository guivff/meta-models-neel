"""Bind E95 metadata to existing banks; no model, judge or runner implementation."""
import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def opaque(bank, item):
    return hashlib.sha256(f'E95:{bank}:{item}'.encode()).hexdigest()[:32]


def sample_strata(strata, fraction, seed):
    """Largest-remainder proportional allocation; seeded ties and sampling."""
    rng = random.Random(seed)
    keys = sorted(strata)
    counts = {k: math.floor(len(strata[k]) * fraction) for k in keys}
    target = round(sum(map(len, strata.values())) * fraction)
    priority = sorted(keys, key=lambda k: (-(len(strata[k])*fraction-counts[k]), rng.random()))
    for k in priority[:target-sum(counts.values())]:
        counts[k] += 1
    result = {k: sorted(rng.sample(strata[k], counts[k])) for k in keys}
    assert sum(map(len, result.values())) == target
    return result


def build(text_root, mech_root, recovered_root):
    base = Path('results/g_agreement/understand')
    probes = {}
    fits_path = mech_root/'cache/g_agreement/understand/e49/verified_section149/out/gates/probe_fits.json'
    probes['e49'] = (fits_path, {x['row']: None for x in read(fits_path) if x['dev_ids']})
    p = recovered_root/base/'e5354/analysis_c9076571_541b23b1/E54_RESULTS.json'
    probes['e54'] = (p, {x['row']: x['probe']['auroc'] for x in read(p)['rows']})
    for bank in ('e56', 'e57', 'e62'):
        p = recovered_root/base/bank/'analysis402_once_2026-10-27/PROBE.json'
        probes[bank] = (p, read(p))
    p = recovered_root/base/'e59/analysis5968_once_2026-10-27/RESULTS.json'
    probes['e59'] = (p, read(p)['probe'])
    e87_audit = read(mech_root/base/'e87/INPUT_AUDIT.json')
    reused = {(x['bank'], x['feature']): x['row_index'] for x in e87_audit['rows']}
    e87 = []
    for p in sorted((mech_root/'cache/g_agreement/understand/e87_draft_v2_seven').glob('shard_*/items.json')):
        e87 += read(p)
    e87.sort(key=lambda x: x['global_index'])
    assert len(e87) == 300
    rows, sources, public, private = [], [], [], []
    for bank in ('e49', 'e54', 'e56', 'e57', 'e59', 'e62'):
        folder = text_root/base/bank/'cache'/('frozen_2026-10-26' if bank == 'e49' else 'bank_2026-10-27_v1')
        items_path = folder/'items.PRIVATE.json'
        bank_seal = read(folder/'BANK_SEAL.json')
        assert digest(items_path) == bank_seal['files']['items.PRIVATE.json']
        records = read(items_path)
        probe_path, eligible = probes[bank]
        sources.append(dict(bank=bank, bank_seal_sha256=digest(folder/'BANK_SEAL.json'),
                            items_sha256=digest(items_path), probe_evidence_sha256=digest(probe_path),
                            probe_evidence=str(probe_path)))
        for feature in sorted(eligible):
            dev = [x for x in records if x['feature'] == feature and x['split'] == 'dev']
            test = [x for x in records if x['feature'] == feature and x['split'] == 'test']
            assert dev and test, (bank, feature)
            selected = test[:30]
            reuse = (bank, feature) in reused
            original = [x for x in e87 if x['global_index']//30 == reused[(bank, feature)]] if reuse else []
            ids, counts = [], []
            index = len(rows)
            for i, x in enumerate(selected):
                endpoint = x.get('read_index', len(x['ids'])-1)
                tokens = x['ids'][:endpoint+1]
                if reuse:
                    assert tokens == original[i]['ids'], (bank, feature, i)
                oid = original[i]['id'] if reuse else opaque(bank, x['id'])
                ids.append(oid)
                counts.append(min(8, len(tokens)))
                public.append(dict(id=oid, global_index=30*index+i, ids=tokens,
                                   read_index=len(tokens)-1, reuse44=False))
                private.append(dict(opaque_id=oid, bank=bank, row=feature, source_id=x['id']))
            rows.append(dict(row_index=index, bank=bank, row=feature, dev_count=len(dev),
                             test_count=len(test), probe_auroc=eligible[feature],
                             probe_exists=True, reuse_e87=reuse, item_ids=ids,
                             nla_position_counts=counts, nla_placebo_count=15,
                             oracle_layers=[20,28,36,44,52,56,60] if reuse else [20,36,44,56],
                             oracle_placebo_count=30 if reuse else 15,
                             e87_row_index=reused.get((bank, feature))))
    assert len(rows) == 80 and sum(r['reuse_e87'] for r in rows) == 10
    assert len(public) == 2400 and len({x['id'] for x in public}) == 2400
    strata = {}
    for row in rows:
        ri = row['row_index']
        pseudos = [hashlib.sha256(f'E95:placebo:{ri}:{i}'.encode()).hexdigest()[:32] for i in range(15)]
        for reader in ('oracle', 'nla'):
            layers = row['oracle_layers'] if reader == 'oracle' else [42]
            real = [f'{oid}:{layer}' for oid in row['item_ids'] for layer in layers]
            if reader == 'oracle' and row['reuse_e87']:
                null = [f'{oid}:{layer}' for oid in row['item_ids'] for layer in layers]
            else:
                null = [f'{oid}:{layer}' for oid in pseudos for layer in layers]
            strata[f'{ri}:real:{reader}'] = real
            strata[f'{ri}:placebo:{reader}'] = null
    chosen = sample_strata(strata, .30, 20261028)
    old = sample_strata(chosen, .25, 20261028)
    return rows, sources, public, private, strata, chosen, old


def main():
    p = argparse.ArgumentParser()
    for key in ('text-root', 'mech-root', 'recovered-root', 'out', 'private-out'):
        p.add_argument('--'+key, required=True, type=Path)
    args = p.parse_args()
    rows, sources, public, private, strata, chosen, old = build(args.text_root, args.mech_root, args.recovered_root)
    args.out.mkdir(parents=True, exist_ok=True)
    args.private_out.mkdir(parents=True, exist_ok=True)
    outputs = {
        'ROW_INVENTORY.json': dict(experiment='E95', reduction_step=0,
            state='BOUND_BASE_INVENTORY_PENDING_FORECAST_AND_NORMS',
            order='bank order E49/E54/E56/E57/E59/E62; row lexical; item order in sealed bank file',
            e87_order_verified=True, rows=rows, sources=sources),
        'JUDGE_INDEX.json': dict(experiment='E95', reduction_step=0, seed=20261028,
            method='largest remainder proportional allocation; seeded ties and sampling without replacement',
            strata='row,condition(real/placebo),reader; unit=item,layer',
            total_universe=sum(map(len, strata.values())), total_selected=sum(map(len, chosen.values())),
            strata_sizes={k: len(v) for k,v in strata.items()}, selected=chosen,
            old_rubric_selected=old, total_old_rubric=sum(map(len, old.values())),
            pending='No call authorization; final source/norm/admission bindings and forecast still required'),
    }
    for name, value in outputs.items():
        (args.out/name).write_text(json.dumps(value, indent=2)+'\n')
    (args.private_out/'public_items.json').write_text(json.dumps(public)+'\n')
    (args.private_out/'SOURCE_MAP.PRIVATE.json').write_text(json.dumps(private)+'\n')
    print(json.dumps(dict(rows=len(rows), reused=10, remaining=70,
        grouped_universe=sum(map(len,strata.values())), judge_selected=sum(map(len,chosen.values())),
        old_rubric_selected=sum(map(len,old.values())), GPU_calls=0, judge_calls=0)))


if __name__ == '__main__':
    main()
