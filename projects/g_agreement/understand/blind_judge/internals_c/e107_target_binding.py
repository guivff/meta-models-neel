"""Copy explicit E107 target bindings using the frozen ID formula, never order."""
import argparse
from .banks import opaque
from .runner import CACHE
from .transport import ROOT, HERE
from ..rubric202 import original_ids
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def target_binding(plans, units, main, original):
    by_id = {}
    for i, p in enumerate(plans):
        ident = opaque('E107', 'outside_judge', p['inventory_id'], p['target'])
        require(ident not in by_id, 'unique explicit inventory/target hash')
        by_id[ident] = (i, p)
    primary = {u['id']: u for u in units if u['kind'] == 'value'}
    olds = {u['id']: u for u in units if u['kind'] == 'old_value'}
    require(len(primary)+len(olds) == len(units) and set(primary) == set(by_id), 'complete unique source units')
    require(sorted(olds) == original_ids(list(primary), 'E107'), 'exact original seeded target-record quarter')
    for ident, (_, p) in by_id.items():
        u = primary[ident]
        require(u['data']['id'] == ident and u['data']['property'] == p['property'] and
                u['data']['values'] == p['values'], 'unchanged original property and target letters')
        if ident in olds:
            require(olds[ident]['data'] == u['data'], 'original comparison is the same outside description/candidates')
    result = []
    for kind, rows, expected in [('value', main, primary), ('old_value', original, olds)]:
        require(len(rows) == len(expected) and {r['id'] for r in rows} == set(expected), 'complete exact judgment ID set')
        for j, row in enumerate(rows):
            require(row['kind'] == kind, 'original judgment kind')
            i, p = by_id[row['id']]
            result.append(dict(judgment_id=row['id'], kind=kind, inventory_id=p['inventory_id'],
                bank=p['bank'], target=p['target'], plan_index=i, judgment_index=j,
                comparison='same outside description, original E56 rubric' if kind == 'old_value' else 'amended E56 rubric',
                code_keys=[j, 'code']))
    return result


def build():
    for name, digest in read(HERE/'E107_TARGET_BINDING_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name) == digest, 'published copy-only target binding source')
    home = CACHE/'E107'
    paths = {
        'plan': (home/'frozen_judge_plan/PLAN_SEAL.json', '3959125782e91f2e3eb7bc02e417f547ff71526a2277f4636f15f469fd02a6fe'),
        'unit': (home/'outside_judge_privacy_copy_units/UNIT_SEAL.json', 'ab4827573be6fd398dad06fd0e14f87c084b232ed5a015c340c9a038eeeb6932'),
        'main': (home/'outside_judge_copy_judging/outputs/JUDGMENT_SEAL.json', 'a44c3a93f422a99208014f501b3e5d5d600323bcd795304a00be3587fec0e472'),
        'original': (home/'outside_judge_copy_original/outputs/JUDGMENT_SEAL.json', 'e3e0e8dcd22a6e2738904c2f099ff5bae3f6f5714981fee799d09e01e1d2ed45'),
        'complete': (home/'complete226/JUDGMENT_SEAL.json', 'c0bcbe02de4a00fbd79d6a59a34dc04bddd717278ebe7b19d21c8650a51fec57')}
    for path, digest in paths.values():
        verify(path, digest)
    plans = read(paths['plan'][0].parent/'PLANS.PRIVATE.json')
    units = read(paths['unit'][0].parent/'UNITS.json')
    main = read(paths['main'][0].parent/'JUDGMENTS.json')
    original = read(paths['original'][0].parent/'JUDGMENTS.json')
    require(len(plans) == len(main) == 4496 and len(original) == 1124, 'full completed E107 target census')
    mapping = target_binding(plans, units, main, original)
    for row in mapping:
        key = 'original' if row['kind'] == 'old_value' else 'main'
        path, digest = paths[key]
        row['code_ref'] = dict(seal=str(path), sha256=digest, member='JUDGMENTS.json', keys=row.pop('code_keys'))
        row['plan_ref'] = dict(seal=str(paths['plan'][0]), sha256=paths['plan'][1], member='PLANS.PRIVATE.json', keys=[row['plan_index']])
    dest = home/'explicit_target_binding'
    dest.mkdir(exist_ok=True)
    seal = dest/'BINDING_SEAL.json'
    if seal.exists():
        verify(seal, sha(seal))
        require(read(dest/'TARGET_BINDINGS.PRIVATE.json') == mapping, 'immutable exact source map')
        return seal
    write(dest/'TARGET_BINDINGS.PRIVATE.json', mapping)
    write(dest/'RECEIPT.json', dict(experiment='E107', n_primary=4496, n_original=1124,
        source_seals={k: dict(seal=str(p), sha256=d) for k, (p, d) in paths.items()},
        identity='opaque(E107,outside_judge,inventory_id,target), verified against all units and judgment IDs',
        original_comparison='seeded25% of 4496 outside target records, same source text/property/candidates with original E56 rubric; not native readouts',
        scientific_analysis=False, model_calls=0, source_seal_sha256=sha(HERE/'E107_TARGET_BINDING_SOURCE_SEAL.json')))
    write(seal, dict(experiment='E107', status='COMPLETE_EXPLICIT_TARGET_BINDING', labels_cpu_only=True,
        files={n: sha(dest/n) for n in ('TARGET_BINDINGS.PRIVATE.json', 'RECEIPT.json')}))
    return seal


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print('E107 explicit CPU target binding '+sha(build()))
