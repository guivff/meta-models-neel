import numpy as np
import pytest
from projects.g_agreement.e96.aggregate import majority, reconstructor_best, reconstruction_error, any_of_16, one_of_16_placebo

V = ('a', 'b')

def test_threshold_and_tie_are_answer_blind():
    assert majority([['a']]*5 + [[]]*11, V)['value'] is None
    assert majority([['a']]*6 + [[]]*10, V)['value'] == 'a'
    rows = [['b']]*6 + [['a']]*6 + [[]]*4
    assert majority(rows, V)['value'] == 'a'
    assert majority(rows, tuple(reversed(V)))['value'] == 'b'

def test_unresolved_never_becomes_silent_and_ambiguity_never_votes():
    with pytest.raises(ValueError): majority([None]*16, V)
    result = majority([['a','b']]*16, V)
    assert result['value'] is None and result['ambiguous_samples'] == 16
    with pytest.raises(ValueError): majority([[]]*15, V)

def test_reconstruction_uses_raw_norm_and_fixed_ties():
    h = np.ones(5120)
    assert reconstruction_error(2*h, h) == 1.0
    assert reconstruction_error(h, h) == 0.0
    result = reconstructor_best([1.0]*16, [True]*16)
    assert result['sample_index'] == 0
    result = reconstructor_best([None, 2.0, 1.0]+[3.0]*13, [False]+[True]*15)
    assert result['sample_index'] == 2
    with pytest.raises(ValueError): reconstructor_best([None]+[1.0]*15, [True]*16)
    with pytest.raises(ValueError): reconstructor_best([float('nan')]*16, [True]*16)
    assert reconstructor_best([None]*16, [False]*16)['status'] == 'SILENT_ALL_MALFORMED'

def test_any_is_descriptive_union_and_placebo_is_one_fixed_opportunity():
    rows = [['a'], ['b']]+[[]]*14
    assert any_of_16(rows, V)['values'] == ['a','b']
    assert one_of_16_placebo(rows, V, 0)['values'] == ['a']
    assert one_of_16_placebo(rows, V, 3)['values'] == []
