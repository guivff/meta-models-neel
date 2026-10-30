"""Count frozen lexical mentions; never infer a lexicon from reader outcomes."""
import re

def require(ok, message):
    if not ok:
        raise ValueError(message)


def named_terms(text, terms, policy):
    """Policy and aliases must be present in the sealed bank binding."""
    require(policy in ('word_exact_casefold', 'word_exact_case_sensitive'), 'unfrozen mention policy')
    require(isinstance(text, str), 'readout text')
    flags = re.IGNORECASE if policy == 'word_exact_casefold' else 0
    found = set()
    for canonical, aliases in terms.items():
        require(isinstance(aliases, list) and aliases and all(isinstance(a, str) and a for a in aliases), 'explicit aliases required')
        if any(re.search(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', text, flags) for alias in aliases):
            found.add(canonical)
    return found


def count_item(records, metadata):
    """One greedy readout per item under 8c66b004."""
    require(len(records) == 1 and {r['repeat'] for r in records} == set(range(1)), 'exactly one greedy readout')
    require(len({(r['reader'], r['unit_id'], r['feature']) for r in records}) == 1, 'mixed items or readers')
    row = records[0]['feature']
    require(row in ('category_switch', 'capacity_list'), 'count row')
    policy = metadata['mention_policy']
    terms = metadata['animal_lexicon'] if row == 'category_switch' else metadata['list_nouns']
    if row == 'capacity_list':
        require(len(terms) == 12, 'twelve distinct list nouns required')
    counts = []
    union = set()
    for r in sorted(records, key=lambda r: r['repeat']):
        found = named_terms(r['text'], terms, policy)
        if row == 'category_switch':
            # None means the last item is a colour, not an animal.
            last = metadata['last_animal_id']
            require(last is None or last in terms, 'last animal identity')
            found.discard(last)
        union |= found
        counts.append({'repeat': r['repeat'], 'named': sorted(found), 'distinct_count': len(found), 'any_mention': bool(found)})
    return {'reader': records[0]['reader'], 'unit_id': records[0]['unit_id'], 'feature': row,
            'per_readout': counts, 'distinct_over_readouts': len(union), 'named_over_readouts': sorted(union),
            'mean_distinct_per_readout': sum(x['distinct_count'] for x in counts) / len(records),
            'any_mention_rate': sum(x['any_mention'] for x in counts) / len(records),
            'independent_items': 1}
