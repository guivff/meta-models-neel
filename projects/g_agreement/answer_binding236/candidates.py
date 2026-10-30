"""Copy sealed E127 values onto original E127/E128 input identities, CPU only."""
import json
from pathlib import Path
from projects.g_agreement.e100.contract import read, sha, verify, write

E127_INPUT = '964b5fc3f7e9e638496b987207cb8eb2ea6af7c54018b764c35452ea5b8462dd'
E128_INPUT = '7e911f6591fb229474b132361b6e67f1696634d0001a3dd4e57823e87194b224'
LABEL_SEAL = '549fa110f6f0f0276dda18b428b26de9c921e9fd97bced195f754a017ebe99c0'
POINTER_SEAL = 'b580ae5a0acf1a96733d8b489b20b1bf3fbae19d926381cad28443687d975f99'


def bind(labels, pointers, e127_items, e128_items):
    """Identity joins only: no outputs, new aliases, value inference or statistics."""
    by_original = {x['original_base_id']: x for x in labels}
    if len(labels) != 84 or len(by_original) != 84:
        raise ValueError('exact original84 candidate identities')
    if any(not isinstance(x[k], str) or not x[k].strip() for x in labels for k in ('old_value', 'new_value')):
        raise ValueError('sealed nonempty candidate strings')
    if any(x['old_value'].casefold() == x['new_value'].casefold() for x in labels):
        raise ValueError('distinct original old/new candidates')
    expected127 = {i: (x, c) for x in labels for c, i in x['condition_ids'].items()}
    if len(expected127) != 252 or len(e127_items) != 252 or {x['id'] for x in e127_items} != set(expected127):
        raise ValueError('complete252 E127 input identities')
    rows = []
    for item in e127_items:
        x, condition = expected127[item['id']]
        if item['base_id'] != x['base_id'] or item['condition'] != condition:
            raise ValueError('E127 sealed condition/base binding')
        rows.append(dict(experiment='E127', id=item['id'], condition=condition, dose=None,
                         original_base_id=x['original_base_id'], old_value=x['old_value'], new_value=x['new_value']))
    pointer_by_id = {x['id']: x for x in pointers}
    if len(pointers) != 336 or len(pointer_by_id) != 336 or len(e128_items) != 336 or {x['id'] for x in e128_items} != set(pointer_by_id):
        raise ValueError('complete336 E128 input/pointer identities')
    seen = set()
    for item in e128_items:
        pointer = pointer_by_id[item['id']]
        x = by_original[pointer['original_base_id']]
        key = (x['original_base_id'], item['alpha'], item['condition'])
        if key in seen or item['alpha'] not in (2, 4) or item['condition'] not in ('steered', 'random'):
            raise ValueError('original84 x doses2/4 x steered/random')
        seen.add(key)
        rows.append(dict(experiment='E128', id=item['id'], condition=item['condition'], dose=item['alpha'],
                         original_base_id=x['original_base_id'], old_value=x['old_value'], new_value=x['new_value']))
    return rows


def build(e127, e128, out):
    """Verify pre-output seals and write a fresh private CPU candidate packet."""
    e127, e128, out = map(Path, (e127, e128, out))
    verify(e127/'inputs', 'INPUT_SEAL.json', E127_INPUT)
    verify(e128/'inputs', 'INPUT_SEAL.json', E128_INPUT)
    verify(e127/'cpu_only', 'LABEL_SEAL.json', LABEL_SEAL)
    verify(e128/'cpu_only', 'POINTER_SEAL.json', POINTER_SEAL)
    rows = bind(read(e127/'cpu_only/LABELS.PRIVATE.json'), read(e128/'cpu_only/ORIGINAL_POINTERS.PRIVATE.json'),
                read(e127/'inputs/items.json'), read(e128/'inputs/items.json'))
    out.mkdir(parents=True, exist_ok=False)
    write(out/'CANDIDATES.PRIVATE.json', rows)
    seal = dict(labels_cpu_only=True, stage_to_pod=False, outcome_files_opened=0,
                source_seals=dict(e127_input=E127_INPUT, e128_input=E128_INPUT,
                                  e127_labels=LABEL_SEAL, e128_pointers=POINTER_SEAL),
                cells={'E127': 252, 'E128': 336}, aliases_added=[],
                files={'CANDIDATES.PRIVATE.json': sha(out/'CANDIDATES.PRIVATE.json')})
    write(out/'CANDIDATE_SEAL.json', seal)
    return dict(cpu_only_root=str(out.resolve()), candidate_seal_sha256=sha(out/'CANDIDATE_SEAL.json'), **seal)
