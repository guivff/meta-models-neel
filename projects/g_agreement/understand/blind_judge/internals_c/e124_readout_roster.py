"""Copy E124's registered readouts and CPU joins; Track Q supplies references."""
import argparse
import json
from .banks import opaque
from .runner import CACHE
from .transport import ROOT, HERE
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def merge(part_a_calls, part_a_join, part_b_units, part_b_custody):
    a = {x['id']: x for x in part_a_join}
    b = {x['id']: x for x in part_b_custody}
    require(len(a) == len(part_a_join) == len(part_a_calls) and
            set(a) == {x['id'] for x in part_a_calls}, 'whole original E118a readout/source join')
    require(len(b) == len(part_b_custody) == len(part_b_units) and
            set(b) == {x['id'] for x in part_b_units}, 'whole original E118b readout/source join')
    rows, joins = [], []
    for call in part_a_calls:
        original = json.loads(call['rendered']['user'])
        require(set(original) == {'id', 'context', 'readout'} and original['id'] == call['id'], 'original frozen E118a fields')
        ident = opaque('E124', 'E118a', original['id'])
        rows.append(dict(id=ident, readout=original['readout']))
        joins.append(dict(a[original['id']], id=ident, source_unit_id=original['id'], source_set='E118a'))
    for unit in part_b_units:
        require(set(unit) == {'id', 'context', 'readout'}, 'original E118b fields')
        ident = opaque('E124', 'E118b', unit['id'])
        rows.append(dict(id=ident, readout=unit['readout']))
        joins.append(dict(b[unit['id']], id=ident, source_unit_id=unit['id'], source_set='E118b'))
    require(len({x['id'] for x in rows}) == len(rows), 'distinct opaque E124 units')
    return sorted(rows, key=lambda x: x['id']), sorted(joins, key=lambda x: x['id'])


def build():
    source = HERE/'E124_READOUT_ROSTER_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items(): require(sha(ROOT/name) == digest, 'published literal E124 roster source')
    a = CACHE/'E118/consistency_judging/INPUT_SEAL.json'
    # This is the original, immutable part-a input, not a regenerated prompt.
    require(sha(a) == read(CACHE/'E118/consistency_judging/outputs/JUDGMENT_SEAL.json')['input_seal_sha256'], 'original E118a input binding')
    verify(a, sha(a))
    b = CACHE/'E118/all_position_roster/UNIT_SEAL.json'
    verify(b, 'eacf843a30acec062587209452823546b6ffad48d3683f5fe6e75f3aebab352e')
    readouts, joins = merge(read(a.parent/'CALLS.json'), read(a.parent/'CPU_JOIN.PRIVATE.json'),
        read(b.parent/'UNITS.json'), read(b.parent/'CUSTODY.PRIVATE.json')['units'])
    require(len(readouts) == 7042 and sum(x['source_set'] == 'E118a' for x in joins) == 252 and
            sum(x['source_set'] == 'E118b' for x in joins) == 6790, 'complete original252 plus all6790 E82 positions')
    dest = CACHE/'E124/readout_roster'
    dest.mkdir(parents=True, exist_ok=True)
    seal = dest/'ROSTER_SEAL.json'
    if seal.exists():
        verify(seal, sha(seal))
        require(read(dest/'READOUTS.json') == readouts and read(dest/'CROSSWALK.PRIVATE.json') == joins, 'immutable E124 source roster')
        return seal
    write(dest/'READOUTS.json', readouts)
    write(dest/'CROSSWALK.PRIVATE.json', joins)
    write(dest/'RECEIPT.json', dict(experiment='E124', n_readouts=7042, n_E118a=252, n_E82_readouts=6790,
        n_E82_items=209, sources=[dict(seal=str(a), sha256=sha(a)), dict(seal=str(b), sha256=sha(b))],
        reference_source='Track Q binding under amendment1 2045d4a96, pending; no model reference created by C',
        wire_context_copied=False, labels_CPU_only=True, new_calls=0, analysis_run=False, source_seal_sha256=sha(source)))
    write(seal, dict(experiment='E124', status='COMPLETE_REGISTERED_READOUT_ROSTER_REFERENCE_BINDING_PENDING',
        files={n: sha(dest/n) for n in ('READOUTS.json', 'CROSSWALK.PRIVATE.json', 'RECEIPT.json')}))
    return seal


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print('E124 readout roster '+sha(build()))
