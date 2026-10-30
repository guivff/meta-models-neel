"""Synthetic tests for the E80c once-only analysis and the family scorers (no real data)."""
import json
import pytest
from . import e80c_analysis as A
from .score80 import passed, quote_verified, chain_hit

BASIC = {'headline_scorer': 'basic', 'family': 'multihop'}
CHAIN = {'headline_scorer': 'chain', 'family': 'chain_intermediates', 'gold_intermediates': [11, 5]}
REGEX = {'headline_scorer': 'regex', 'family': 'multilingual_multihop'}


def test_family_scorers():
    assert passed({'status': 'KEPT', 'result': {'expressed': True, 'target': 'iron', 'quote': 'Iron'}}, BASIC, 'the iron ore') is True
    assert passed({'status': 'KEPT', 'result': {'expressed': True, 'target': 'iron', 'quote': 'gold'}}, BASIC, 'the iron ore') is False  # unverified quote
    assert passed({'status': 'UNPARSEABLE', 'result': None}, BASIC, 'x') is None
    assert passed({'status': 'KEPT', 'result': {'states_value': True, 'values': [11, 3], 'basis': 'arithmetic', 'quote': '11'}}, CHAIN, 'so 11 then') is True
    assert passed({'status': 'KEPT', 'result': {'states_value': True, 'values': [12], 'basis': 'arithmetic', 'quote': '12'}}, CHAIN, '12') is False
    assert not chain_hit({'values': [110], 'quote': ''}, [11], '110 items')  # whole numbers only
    assert passed({'status': 'CPU_REGEX', 'result': {'pass': True}}, REGEX, 'x') is True
    assert passed({'status': 'KEPT', 'result': {}}, REGEX, 'x') is None
    assert quote_verified('café', ['CAFE!']) and not quote_verified('  ', ['x'])


def make(n_items, none, conds):
    items = [f'E80:multihop:{k:03d}' for k in range(n_items)]
    none_v = {i: none(k) for k, i in enumerate(items)};cond_v = {c: {i: f(k) for k, i in enumerate(items)} for c, f in conds.items()}
    return items, none_v, cond_v


def test_rule_met_falsified_pca_and_missing():
    items, n, c = make(100, lambda k: True, {'J_ablated': lambda k: k >= 60, 'random_ablated': lambda k: k >= 5, 'PCA_ablated': lambda k: k >= 20})
    r = A.rule(n, c, items)
    assert r['status'] == 'MET' and abs(r['falls']['J_ablated']-0.60) < 1e-9 and r['J_minus_random']['ci95'][0] > 0
    items, n, c = make(100, lambda k: True, {'J_ablated': lambda k: k >= 10, 'random_ablated': lambda k: k >= 8, 'PCA_ablated': lambda k: k >= 5})
    assert A.rule(n, c, items)['status'].startswith('FALSIFIED')
    items, n, c = make(100, lambda k: True, {'J_ablated': lambda k: k >= 60, 'random_ablated': lambda k: k >= 5, 'PCA_ablated': lambda k: k >= 58})
    assert 'high-variance directions' in A.rule(n, c, items)['status']
    items, n, c = make(10, lambda k: k < 6, {'J_ablated': lambda k: None if k == 0 else False, 'random_ablated': lambda k: True, 'PCA_ablated': lambda k: True})
    r = A.rule(n, c, items);assert r['n_pass_none'] == 6 and r['n_complete'] == 5 and r['n_excluded_missing'] == 1
    items, n, c = make(4, lambda k: False, {x: (lambda k: True) for x in A.CONDITIONS})
    assert A.rule(n, c, items)['status'] == 'NOT EVALUABLE'


def test_bootstrap_deterministic():
    items, n, c = make(40, lambda k: True, {'J_ablated': lambda k: k % 2 == 0, 'random_ablated': lambda k: k % 5 != 0, 'PCA_ablated': lambda k: k % 3 != 0})
    assert A.rule(n, c, items) == A.rule(n, c, items)


def test_once_guard_and_pins(tmp_path):
    spec = {'guard': str(tmp_path/'GUARD.json'), 'out': str(tmp_path/'out'), 'pins': {str(tmp_path/'x'): '0'*64}}
    (tmp_path/'x').write_text('x');(tmp_path/'SPEC.json').write_text(json.dumps(spec))
    import sys
    sys.argv = ['e80c', '--spec', str(tmp_path/'SPEC.json')]
    with pytest.raises(ValueError, match='input pin'):A.main()
    assert not (tmp_path/'GUARD.json').exists()  # failed pins never consume the guard
    (tmp_path/'GUARD.json').write_text('{}')
    with pytest.raises(ValueError, match='once only'):A.main()


def test_missingness_bounds():
    from .e80c_bounds import bounds
    items, n, c = make(10, lambda k: True, {'J_ablated': lambda k: None if k < 2 else False, 'random_ablated': lambda k: True, 'PCA_ablated': lambda k: True})
    b = bounds(n, c, items)
    assert b['missing_as_pass']['falls']['J_ablated'] == 0.8 and b['missing_as_fail']['falls']['J_ablated'] == 1.0
    assert b['missing_by_condition']['J_ablated'] == 2 and b['n_pass_none'] == 10
