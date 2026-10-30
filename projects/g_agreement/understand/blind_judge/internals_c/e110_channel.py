"""Prospective E11010 outside/E82 channels; no selector or scientific analysis.

The sealed source contract is CPU-only. Its owner binds the unchanged selected
roster, public prefixes and per-system candidate letters before any outside or
judging output. An eligible complete native seal is mandatory. No E82 reference
readout, old TwoHopFact result or partial filter can enter this channel.
"""
import argparse
import time
from collections import Counter
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from . import registered, runner, transport
from .accounting226 import snapshot
from .banks import opaque
from ..rubric202 import amended, BASE, original_ids
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

CAP = Decimal('10')
INSTRUCTION = 'Describe what is going on in this text and what comes next.'
SYSTEMS = ('oracle', 'nla', 'outside')


def validate_source(source):
    require(source['experiment'] == 'E110' and source['deviation'] == 2 and
            source['labels_cpu_only'] is True and source['all_selected_survivors_retained'] is True and
            source['original_TwoHopFact_reused'] is False and source['E82_reference_rejudged'] is False,
            'new complete deviation2 source only, no old or reference acquisition')
    items = source['items']; n = len(items)
    require(60 <= n <= 3000 and len({x['id'] for x in items}) == n,
            'full frozen variable selected grid')
    counts = Counter(x['cohort'] for x in items)
    require(set(counts) <= {'belief_wrong', 'belief_right'} and counts['belief_wrong'] >= 60 and
            source['survivor_counts'] == dict(counts), 'source-bound floor and whole cohort')
    require(source['selection_mode'] in ('stable belief', 'no paraphrase gate'), 'eligible original selection mode')
    for x in items:
        require(type(x['prompt']) is str and bool(x['prompt']) and type(x['property']) is str and
                set(x['values_by_system']) == set(x['target_letters_by_system']) == set(SYSTEMS),
                'exact original full public prefix and three source-bound candidate orders')
        meanings = []
        for system in SYSTEMS:
            values = x['values_by_system'][system]; letters = x['target_letters_by_system'][system]
            require(set(values) == {'A', 'B'} and set(letters) == {'belief', 'truth'} and
                    set(letters.values()) == {'A', 'B'} and all(bool(v) for v in values.values()),
                    'explicit original truth and belief values/letters, no undefined candidate')
            meanings.append({k: values[v] for k, v in letters.items()})
        require(all(v == meanings[0] for v in meanings), 'same source meanings across original system letter orders')
    return items


def outside_calls(source):
    return [dict(id=opaque('E110', 'outside', x['id']), phase='generation',
                 rendered=dict(system=None, user=x['prompt']+'\n'+INSTRUCTION, schema=None))
            for x in validate_source(source)]


def make_units(source, native, generated):
    items = validate_source(source); by = {x['id']: x for x in items}
    texts = {}; pointers = {}
    for x in native:
        key = (x['item_id'], x['reader'])
        require(key[0] in by and key[1] in ('oracle', 'nla') and key not in texts and
                x['layer'] == (44 if key[1] == 'oracle' else 42) and type(x['text']) is str,
                'one original complete native readout per selected item/reader')
        texts[key] = x['text']; pointers[key] = x['source_ref']
    require(set(texts) == {(i, r) for i in by for r in ('oracle', 'nla')}, 'all native outputs, no partial stitching')
    gen = {x['id']: x for x in generated}
    require(len(gen) == len(generated) == len(items) and
            set(gen) == {opaque('E110', 'outside', i) for i in by}, 'full new outside generation')
    units = []; joins = []
    for item in items:
        g = gen[opaque('E110', 'outside', item['id'])]
        require(g['status'] == 'GENERATED' and g['phase'] == 'generation' and
                g['finish_reason'] in ('stop', 'length') and type(g['text']) is str and
                g.get('refusal') is None, 'retain full outside text including length truncations')
        for system in SYSTEMS:
            key = (item['id'], system); ident = opaque('E110', system, item['id'])
            text = g['text'] if system == 'outside' else texts[key]
            units.append(dict(id=ident, kind='value', rubric=amended().decode(),
                              data=dict(id=ident, property=item['property'],
                                        values=item['values_by_system'][system], readout=text)))
            joins.append(dict(id=ident, item_id=item['id'], system=system,
                              target_letters=item['target_letters_by_system'][system],
                              source_ref=dict(generation_id=g['id']) if system == 'outside' else pointers[key]))
    selected = set(original_ids([x['id'] for x in units], 'E110'))
    units += [dict(x, kind='old_value', rubric=BASE.read_text()) for x in units if x['id'] in selected]
    return units, joins


def source_gate():
    for name, digest in read(transport.HERE/'E110_CHANNEL_SOURCE_SEAL.json')['files'].items():
        require(sha(transport.ROOT/name) == digest, 'published E110 channel source')


def load_source(path, digest):
    seal = verify(path, digest)
    require(seal['experiment'] == 'E110' and seal['status'] == 'COMPLETE_ELIGIBLE_SOURCE' and
            seal['frozen_before_reader_outputs'] is True, 'complete owner frozen selection/native contract')
    require({'SOURCE_INPUTS.PRIVATE.json', 'NATIVE_TEXTS.PRIVATE.json'} <= set(seal['files']), 'complete CPU source bindings')
    roles = set(); sources = {}
    for ref in seal['source_seals']:
        original = verify(ref['seal'], ref['sha256']); roles.add(ref['role'])
        sources[(str(Path(ref['seal']).resolve()), ref['sha256'])] = original
        if ref['role'] == 'native': require(original['status'] == 'COMPLETE' and original['experiment'] == 'E110', 'only complete original native output seal')
    require(roles >= {'selection', 'native', 'public_inputs', 'original_item_source'}, 'all original source epochs bound')
    source = read(path.parent/'SOURCE_INPUTS.PRIVATE.json'); validate_source(source)
    native = read(path.parent/'NATIVE_TEXTS.PRIVATE.json')
    def original_value(ref):
        key = (str(Path(ref['seal']).resolve()), ref['sha256'])
        require(key in sources and ref['member'] in sources[key]['files'], 'reference is in the verified original whole source')
        value = read(Path(ref['seal']).parent/ref['member'])
        for k in ref['keys']: value = value[k]
        return value
    for item in source['items']:
        require(original_value(item['public_prompt_ref']) == item['prompt'], 'unchanged original full public prefix')
    for row in native:
        require(original_value(row['source_ref']) == row['text'], 'byte-exact native text from its original complete seal')
    expected = {(x['id'], r) for x in source['items'] for r in ('oracle', 'nla')}
    require(len(native) == len(expected) and {(x['item_id'], x['reader']) for x in native} == expected and
            all(x['layer'] == (44 if x['reader'] == 'oracle' else 42) and type(x['text']) is str for x in native),
            'whole original native grid before any outside call')
    return seal, source, native


def check_scope(bank, units, custody):
    require(bank == 'E110' and custody['experiment'] == bank and custody['verified'] is True and
            custody['complete_eligible_native_grid'] is True and custody['labels_cpu_only'] is True,
            'complete E110 owner custody')
    n = custody['selected_items']; counts = Counter(x['kind'] for x in units)
    ids = [x['id'] for x in units if x['kind'] == 'value']
    require(60 <= n <= 3000 and counts['value'] == 3*n and
            set(counts) == {'value', 'old_value'} and
            sorted(x['id'] for x in units if x['kind'] == 'old_value') == original_ids(ids, 'E110'),
            'all three systems and exact registered original comparison')


@contextmanager
def worker():
    source_gate(); prior = transport.CAPS.get('E110')
    require(prior in (None, CAP), 'same separate E110 lifetime10')
    transport.CAPS['E110'] = CAP
    saved = {name: getattr(registered, name) for name in ('HERE', 'check_scope', 'snapshot', 'Transport')}
    old_snapshot, old_transport = runner.snapshot, runner.Transport
    registered.HERE = transport.HERE/'E110'; registered.check_scope = check_scope
    registered.snapshot = runner.snapshot = snapshot
    registered.Transport = runner.Transport = E110Transport
    try: yield
    finally:
        runner.snapshot, runner.Transport = old_snapshot, old_transport
        for name, value in saved.items(): setattr(registered, name, value)
        if prior is None: transport.CAPS.pop('E110', None)
        else: transport.CAPS['E110'] = prior


class E110Transport(transport.Transport):
    def __init__(self, path, digest, admission, key):
        require(admission['bank'] == 'E110' and Decimal(str(admission['allocation_usd'])) == CAP,
                'E110 original separate10 lifetime allocation only')
        require(admission['E110_source_seal_sha256'] == sha(transport.HERE/'E110_CHANNEL_SOURCE_SEAL.json'),
                'posted immutable E110 source receipt')
        super().__init__(path, digest, admission, key)


def prepare(source_path, digest, action):
    owner, source, native = load_source(source_path, digest)
    ref = dict(seal=str(source_path), sha256=digest)
    if action == 'prepare-generation':
        dest = runner.seal_phase('E110', 'generation', outside_calls(source),
            dict(owner_source_sha256=digest, full_prefix=True, selected_items=len(source['items'])), [ref]+owner['source_seals'])
        return [dict(directory=str(dest), preflight=runner.preflight(dest))]
    generation = runner.CACHE/'E110/generation/outputs/GENERATION_SEAL.json'
    g = verify(generation, sha(generation))
    require(g['status'] == 'COMPLETE' and g['experiment'] == 'E110' and g['route_verified'] is True,
            'whole approved-route generation before judging')
    units, joins = make_units(source, native, read(generation.parent/'RESPONSES.json'))
    dest = runner.CACHE/'E110/selected_value_units'; dest.mkdir(parents=True, exist_ok=True); dest.chmod(0o700)
    if (dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json', sha(dest/'UNIT_SEAL.json'))
        require(read(dest/'UNITS.json') == units, 'immutable full E110 units')
    else:
        write(dest/'UNITS.json', units); write(dest/'SOURCE_POINTERS.PRIVATE.json', joins)
        write(dest/'CUSTODY.json', dict(issuer='W-internals-C', experiment='E110', verified=True,
            labels_cpu_only=True, selected_items=len(source['items']), complete_eligible_native_grid=True,
            source_seals=[ref, dict(seal=str(generation), sha256=sha(generation))]))
        write(dest/'UNIT_SEAL.json', dict(experiment='E110', files={p.name:sha(p) for p in dest.iterdir() if p.is_file()}))
    spec = dest/'PREPARE_SPEC.json'
    write(spec, dict(bank='E110', unit_seal=str(dest/'UNIT_SEAL.json'), unit_sha256=sha(dest/'UNIT_SEAL.json'), phase_name='selected_value'))
    return registered.prepare(spec)


def run_generation(dest):
    admission = read(dest/'ADMISSION.json'); live = dest/'LIVE_PROOF.PRIVATE.json'
    require(sha(live) == admission['live_route_funding_proof_sha256'], 'published exact live phase proof')
    proof = read(live)
    require(0 <= time.time()-proof['at_epoch'] < 300 and all(proof[k] is True for k in
            ('route_verified', 'account_privacy_verified', 'funded_remaining_bank_cap')), 'fresh live route/privacy/funding')
    return runner.run(dest)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare-generation', 'prepare-judging', 'run-generation', 'run-judging'))
    p.add_argument('--source-seal', type=Path); p.add_argument('--source-sha256'); p.add_argument('--phase-directory', type=Path)
    a = p.parse_args()
    with worker():
        if a.action.startswith('prepare'): print(prepare(a.source_seal, a.source_sha256, a.action))
        elif a.action == 'run-generation': run_generation(a.phase_directory)
        else: registered.run(a.phase_directory)
