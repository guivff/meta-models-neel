"""Synthetic tests for the E87 R-L1 analysis (no real data)."""
import json
import pytest
from . import e87_analysis as A


def code(i, cat, vals=(), pos=None):
    return dict(id=i, category=cat, values=list(vals), evidence='' if cat == 'silent' else 'x', first_position=pos)


def build(real_rate, plac_rate, rows=A.MISSED+A.CONTROLS, n=30, unparse=0):
    """real_rate/plac_rate: row -> share of items stating the correct value at the best layer (44); others silent."""
    J, C = [], []
    for r in rows:
        for k in range(n):
            for arm in ('real', 'placebo'):
                rate = (real_rate if arm == 'real' else plac_rate)(r)
                for L in A.ORACLE_LAYERS:
                    gid = f'{r}:{k}:{arm}:{L}'
                    J.append(dict(id=gid, public_item_id=f'{r}:{k}', row=r, reader='oracle', arm=arm, layer=L, target='A'))
                    if k < unparse and L == 20 and arm == 'real':C.append(code(gid, 'UNPARSEABLE'))
                    elif L == 44 and k < rate*n:C.append(code(gid, 'states_value', ['A'], 3))
                    else:C.append(code(gid, 'silent'))
            gid = f'{r}:{k}:nla'
            J.append(dict(id=gid, public_item_id=f'{r}:{k}', row=r, reader='nla', arm='real', layer=42, target='A'));C.append(code(gid, 'states_value', ['B'], 1))
    return C, J


def run(C, J):
    cells, first = A.grid(C, J)
    per = {r: A.row_stat(cells, r) for r in A.MISSED+A.CONTROLS}
    return per, A.verdict(per, A.MISSED), A.verdict(per, tuple(r for r in A.MISSED if r != A.SENSITIVITY_DROP)), cells


def test_signed_score():
    assert A.signed(code('a', 'states_value', ['A']), 'A') == 1 and A.signed(code('a', 'states_value', ['B']), 'A') == -1
    assert A.signed(code('a', 'states_value', ['A', 'B']), 'A') == 0 and A.signed(code('a', 'silent'), 'A') == 0
    assert A.signed(code('a', 'UNPARSEABLE'), 'A') is None


def test_met_when_blind_spot_survives_and_controls_pass():
    ctrl = set(A.CONTROLS)
    per, v, s, _ = run(*build(lambda r: 0.6 if r in ctrl else 0.05, lambda r: 0.0))
    assert v['status'] == 'MET' and v['rows_D_le_0_10'] == 8 and v['controls_ok']
    assert abs(per['topic_twin']['D'] - 0.6) < 1e-9 and per['topic_twin']['S_layer_real']['44'] == pytest.approx(0.6)
    assert s['status'] == 'MET' and s['rows'] == 7


def test_falsified_and_not_evaluable():
    ctrl = set(A.CONTROLS)
    _, v, _, _ = run(*build(lambda r: 0.6 if r in ctrl else (0.3 if r in A.MISSED[:4] else 0.0), lambda r: 0.0))
    assert v['status'].startswith('FALSIFIED') and v['rows_D_ge_0_20'] == 4
    _, v, _, _ = run(*build(lambda r: 0.1 if r == 'loop_direction' else (0.6 if r in ctrl else 0.0), lambda r: 0.0))
    assert v['status'].startswith('NOT EVALUABLE')


def test_placebo_subtracts_any_of_many_inflation_and_missing_kept():
    ctrl = set(A.CONTROLS)
    per, v, _, cells = run(*build(lambda r: 0.6 if r in ctrl else 0.3, lambda r: 0.25, unparse=3))
    assert per['branch_taken']['D'] == pytest.approx((9-8)/30, abs=1e-9) and v['status'] == 'MET'  # 9 real vs 8 placebo items
    assert per['branch_taken']['unparseable']['real'] == 3
    assert sum(x is None for x in cells[('branch_taken', 'oracle', 'real', 20)].values()) == 3


def test_complete_grid_required_and_once_guard(tmp_path):
    C, J = build(lambda r: 0.0, lambda r: 0.0, rows=('topic_twin',), n=2)
    with pytest.raises(ValueError, match='complete grouped grid'):A.grid(C[:-1], J)
    spec = {'guard': str(tmp_path/'G.json'), 'out': str(tmp_path/'o'), 'pins': {str(tmp_path/'x'): '0'*64}}
    (tmp_path/'x').write_text('x');(tmp_path/'S.json').write_text(json.dumps(spec))
    import sys
    sys.argv = ['e87', '--spec', str(tmp_path/'S.json')]
    with pytest.raises(ValueError, match='input pin'):A.main()
    assert not (tmp_path/'G.json').exists()
    (tmp_path/'G.json').write_text('{}')
    with pytest.raises(ValueError, match='once only'):A.main()


def test_depth_classes_floor_and_figure(tmp_path):
    from . import e87_depth as Dp
    assert Dp.classify({20: True, 28: False, 36: False, 44: True, 52: False, 60: False}) == 'persistent'
    assert Dp.classify({20: False, 28: True, 36: False, 44: False, 52: False, 60: False}) == 'consumed'
    assert Dp.classify({20: False, 28: False, 36: False, 44: False, 52: True, 60: False}) == 'late'
    assert Dp.classify({L: False for L in Dp.FIG_LAYERS}) == 'never'
    assert Dp.classify({20: False, 28: False, 36: False, 44: True, 52: False, 60: False}).startswith('outside')
    ctrl = set(A.CONTROLS)
    C, J = build(lambda r: 0.6 if r in ctrl else 0.05, lambda r: 0.0)
    cells, _ = A.grid(C, J)
    prof = Dp.profile(cells, Dp.first_by_layer(C, J), {'topic_twin': 0.45})
    assert prof['topic_twin']['floor']['44'] == 0.45 and prof['topic_twin']['class'] == 'never'  # 0.6 - 0.45 < 0.20
    assert prof['loop_direction']['class'].startswith('outside') and prof['loop_direction']['first_mention_median']['44'] == 3
    assert prof['branch_taken']['class'] == 'never' and prof['branch_taken']['real']['44']['ci95'] is not None
    Dp.figure(prof, {'unit_system:36': {'estimate': 0.7, 'CI95': [0.6, 0.8]}}, tmp_path/'f.png')
    assert (tmp_path/'f.png').stat().st_size > 10000


def test_control_gate_precedes_falsifier():
    # loop_direction control fails AND 4 MISSED rows would meet the falsifier: must be NOT EVALUABLE, not FALSIFIED.
    _, v, s, _ = run(*build(lambda r: 0.1 if r == 'loop_direction' else (0.6 if r == 'topic_twin' else (0.3 if r in A.MISSED[:4] else 0.0)), lambda r: 0.0))
    assert v['rows_D_ge_0_20'] == 4 and not v['controls_ok'] and v['status'].startswith('NOT EVALUABLE')
    assert s['status'].startswith('NOT EVALUABLE')  # the 7-row sensitivity line obeys the same gate


def test_negative_placebo_floor_clamped_at_zero():
    # Clarification 4: a negative placebo S_layer never lowers the floor below 0 (raw 0 vs placebo -0.25 does not count).
    from . import e87_depth as Dp
    J, C = [], []
    for k in range(4):
        for arm in ('real', 'placebo'):
            for L in A.ORACLE_LAYERS:
                gid = f'r:{k}:{arm}:{L}';J.append(dict(id=gid, public_item_id=f'r:{k}', row='branch_taken', reader='oracle', arm=arm, layer=L, target='A'))
                C.append(code(gid, 'states_value', ['B'], 1) if arm == 'placebo' and k == 0 else code(gid, 'silent'))
    cells, _ = A.grid(C, J)
    prof = Dp.profile(cells, {}, {})['branch_taken']
    assert prof['placebo']['44']['S'] == -0.25 and prof['floor']['44'] == 0.0 and prof['class'] == 'never'
