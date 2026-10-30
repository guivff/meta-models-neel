import copy
import pytest
from .candidates import bind


def sources():
    labels, pointers, a, b = [], [], [], []
    for n in range(84):
        base = f'original-{n}'
        conditions = {c: f'E127-{n}:{c}' for c in ('context_update', 'neutral_prefix', 'none')}
        labels.append(dict(original_base_id=base, base_id=f'E127-{n}', old_value='Paris' if n % 2 else 'Lima',
                           new_value='Lima' if n % 2 else 'Paris', condition_ids=conditions))
        a.extend(dict(id=i, base_id=f'E127-{n}', condition=c) for c, i in conditions.items())
        for dose in (2, 4):
            for condition in ('steered', 'random'):
                ident = f'E128-{n}:{dose}:{condition}'
                pointers.append(dict(id=ident, original_base_id=base))
                b.append(dict(id=ident, alpha=dose, condition=condition))
    return labels, pointers, a, b


def test_values_are_copied_without_orientation_or_condition_changes():
    rows = bind(*sources())
    assert len(rows) == 588
    assert rows[0]['old_value'] == 'Lima' and rows[0]['new_value'] == 'Paris'
    assert rows[3]['old_value'] == 'Paris' and rows[3]['new_value'] == 'Lima'
    assert {r['condition'] for r in rows if r['experiment'] == 'E127'} == {'context_update', 'neutral_prefix', 'none'}
    assert all(r['old_value'] != r['new_value'] for r in rows)


@pytest.mark.parametrize('source', range(4))
def test_incomplete_or_duplicate_sources_refused(source):
    xs = sources()
    xs[source][-1] = copy.deepcopy(xs[source][0])
    with pytest.raises(ValueError):
        bind(*xs)


def test_condition_swap_refused():
    xs = sources()
    xs[2][0]['condition'] = 'none'
    with pytest.raises(ValueError):
        bind(*xs)


def test_same_old_new_refused():
    xs = sources()
    xs[0][0]['new_value'] = xs[0][0]['old_value']
    with pytest.raises(ValueError):
        bind(*xs)
