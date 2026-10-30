"""Literal all-position E82 roster after W-mech2's registered source-case ruling."""
import argparse
import subprocess
from pathlib import Path
from .runner import CACHE
from .transport import ROOT, HERE
from .banks import opaque
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def roster(public, joins, grouped, native):
    contexts = {x['id']: (i, x) for i, x in enumerate(public)}
    groups = {x['id']: (i, x) for i, x in enumerate(grouped)}
    records = {(x['unit_id'], x['position'], x['reader']): (i, x) for i, x in enumerate(native)}
    require(len(contexts) == len(public) and len(groups) == len(grouped) and len(records) == len(native), 'unique original source identities')
    oracle = [x for x in joins if x['reader'] == 'oracle']
    require(len({x['id'] for x in oracle}) == len(oracle) and
            {x['source_public_id'] for x in oracle} == set(contexts), 'whole original Oracle item census')
    units, pointers, used = [], [], set()
    for j in oracle:
        pi, p = contexts[j['source_public_id']]
        gi, g = groups[j['id']]
        positions = [x['position'] for x in g['positions']]
        require(len(set(positions)) == len(positions) and set(positions) == set(p['read_positions']), 'every original position, no primary selection')
        for pos in g['positions']:
            key = (j['source_public_id'], pos['position'], 'oracle')
            ni, n = records[key]
            require(n['text'] == pos['readout'], 'exact native readout, no merge or rewrite')
            ident = opaque('E118b', j['id'], str(pos['position']))
            units.append(dict(id=ident, context=p['prompt'], readout=n['text']))
            pointers.append(dict(id=ident, item_id=j['source_public_id'], group_id=j['id'], family=j['family'],
                position=pos['position'], public_index=pi, grouped_index=gi, native_index=ni))
            used.add(key)
    require(used == {key for key in records if key[2] == 'oracle'}, 'no unaccounted native Oracle readout')
    return units, pointers


def build():
    for name, digest in read(HERE/'E82_CONSISTENCY_ROSTER_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name) == digest, 'published literal roster source')
    base = ROOT.parent
    original = base/'wt-i2/cache/g_agreement/i2/e82_judge_cpu_v1'
    public = base/'wt-wtext/results/g_agreement/understand/e82/cache/workspacebench_2026-10-28_v2/PUBLIC_CAPTURE.json'
    grouped, join = original/'GROUPED_READOUTS.json', original/'JOIN_MAP.PRIVATE.json'
    expected = [(public, 'f3ba509891acc30505895f21d8518804354c887d8823a303bb23836426822ad4'),
        (grouped, 'd1ccfa2ce8283d2c36e509ae1a99d257208d27175539f55d28b25a7294e60b76'),
        (join, '08176c1ac79e04f47fda603b2493784c7cfd695886ecb95978d0446ebe41a7ef')]
    for path, digest in expected: require(sha(path) == digest, 'exact original E82 public/group/join bytes')
    native_seal = base/'wt-i2/cache/g_agreement/i2/section212_restarts_v1/e82-full-a1/terminal_pull/outputs/OUTPUT_SEAL.json'
    ns = verify(native_seal, 'f9fd7603fccdadb2ed1c412801833e2d8979fe49a10a1695d3a88d4e6defa2fa')
    judge_seal = original/'judging/E82_judgments/RESULT_SEAL.json'
    verify(judge_seal, 'fd09388fb1a55b2e855fbef11d29e9ab8cc848b3e53dbedd2d5883af7200ae52')
    tm = original/'grouped_adapter_v1/TARGET_MAP.PRIVATE.json'
    require(sha(tm) == '26de7997d18081750290026800219fe5ed142420fce9c92c849549be50504336', 'original target map')
    judgments = read(judge_seal.parent/'JUDGMENTS.json')
    ji = {x['id']: i for i, x in enumerate(judgments)}
    targets = {(x['group_id'], x['target']): x for x in read(tm)}
    native, source_refs = [], []
    for member in ns['files']:
        if not member.startswith('jobs/') or not member.endswith('.json'): continue
        rows = read(native_seal.parent/member)
        for i, row in enumerate(rows):
            if row['reader'] != 'oracle': continue
            native.append(row)
            source_refs.append(dict(seal=str(native_seal), sha256=sha(native_seal), member=member, keys=[i, 'text']))
    units, pointers = roster(read(public), read(join), read(grouped), native)
    require(len(units) == 6790 and len({x['item_id'] for x in pointers}) == 209, 'all6790 Oracle readouts/all209 original items')
    for p in pointers:
        p['readout_ref'] = source_refs[p.pop('native_index')]
        p['context_ref'] = dict(path=str(public), sha256=sha(public), keys=[p.pop('public_index'), 'prompt'])
        p['original_label_refs'] = {}
        for target in ('belief', 'truth'):
            t = targets.get((p['group_id'], target))
            p['original_label_refs'][target] = None if t is None else dict(seal=str(judge_seal), sha256=sha(judge_seal),
                member='JUDGMENTS.json', keys=[ji[t['id']], 'code'], target_letter=t['target_letter'])
        require(p['original_label_refs']['belief'] is not None, 'original belief target present for every item')
    require(len({p['item_id'] for p in pointers if p['original_label_refs']['truth'] is None}) == 10,
            'all ten original no-truth items retained without an invented truth target')
    dest = CACHE/'E118/all_position_roster'
    dest.mkdir(parents=True, exist_ok=True)
    final = dest/'UNIT_SEAL.json'
    if final.exists():
        verify(final, sha(final))
        require(read(dest/'UNITS.json') == units and read(dest/'CUSTODY.PRIVATE.json')['units'] == pointers, 'immutable literal source roster')
        return final
    case_commit = '408f2c23f28e544fd5c053a65c70fab7883d6249'
    owner = subprocess.check_output(['git', 'show', case_commit+':results/g_agreement/r/WMECH2_HANDOFF.md'], cwd=ROOT, text=True)
    case = owner.split('## W-mech2 §217 intake: E118b clarification1 source-case determination', 1)[1].split('\n## ', 1)[0]
    require('NO single registered primary position' in case and 'all-position branch applies' in case, 'published W-mech2 source-case ruling')
    write(dest/'OWNER_CASE_RECEIPT.json', dict(commit=case_commit, path='results/g_agreement/r/WMECH2_HANDOFF.md', exact_text=case))
    write(dest/'UNITS.json', units)
    write(dest/'CUSTODY.PRIVATE.json', dict(experiment='E118', phase='part_b', n_readouts=6790, n_items=209,
        analysis_unit='item; average within item and bootstrap items; never positions as independent items',
        scientific_report_adapter_pending=True, original_group_labels_not_position_labels=True, units=pointers,
        original_source_files=[dict(path=str(p), sha256=d) for p, d in expected], target_map_sha256=sha(tm)))
    write(final, dict(experiment='E118', phase='part_b', n=6790, n_items=209,
        frozen_before_judging=True, unit_definition_frozen=True, labels_cpu_only=True,
        source_seals=[dict(seal=str(native_seal), sha256=sha(native_seal)), dict(seal=str(judge_seal), sha256=sha(judge_seal))],
        files={n: sha(dest/n) for n in ('UNITS.json', 'CUSTODY.PRIVATE.json', 'OWNER_CASE_RECEIPT.json')}))
    return final


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print('E82 all-position consistency roster '+sha(build()))
