"""Lossless E56 judgment adaptation; both-value assertions contribute zero to S."""
from .contract import require, read, sha, verify


def adapt(record):
    result = dict(record)
    category = record['category']
    if category == 'names_property':
        category = 'names_property_without_value'
    require(category in ('states_value', 'names_property_without_value', 'exhibits', 'silent'), 'judgment category')
    values = record.get('values')
    if values is None:
        values = [] if record.get('value') is None else [record['value']]
    require(isinstance(values, list) and len(values) == len(set(values)) and set(values) <= {'A', 'B'}, 'judgment values')
    require(bool(values) == (category == 'states_value'), 'category/value consistency')
    result.update(category=category, values=list(values))
    return result


def bucket(record, truth):
    r = adapt(record)
    if r['category'] != 'states_value':
        return r['category']
    if len(r['values']) == 2:
        return 'states_value_both'
    return 'states_value_correct' if truth in r['values'] else 'states_value_wrong'


def context_binding(context, context_seal, here):
    binding = read(here/'CONTEXT_BINDING.json')
    require(sha(context/'MAP.json') == binding['map_sha256'], 'exact c9076571 map binding')
    require(context_seal.get('judgment_delivery_seal_sha256') == binding['judgment_delivery_seal_sha256'], 'exact judgment delivery binding')
    require(context_seal.get('private_key_sha256') == binding['private_key_sha256'], 'integrator join key binding')
    delivery = binding['judgment_delivery_path']
    verify(delivery, 'RESULT_SEAL.json', binding['judgment_delivery_seal_sha256'])
    from pathlib import Path
    original = read(Path(delivery)/'JUDGMENTS.json')
    codes = {x['id']: x for x in original}
    joined = read(context/'JUDGMENTS.json')
    require(len(joined) == len(codes) == 336 and {x['blind_id'] for x in joined} == set(codes), 'lossless opaque judgment join')
    for row in joined:
        code = codes[row['blind_id']]
        require(all(row[k] == code[k] for k in ('category', 'values', 'evidence')), 'delivered judgment changed')
