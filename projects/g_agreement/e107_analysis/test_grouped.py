import pytest
from .adapter import code


def c(evidence='chosen value'):
    return dict(id='synthetic',category='states_value',values=['A'],evidence=evidence)


def test_original_all_positions_group_code():
    positions=[dict(position=0,readout='unrelated'),dict(position=7,readout='The chosen value is here.')]
    original=c()
    assert code(original,positions,'A',grouped=True) is original
    assert code(original,list(reversed(positions)),'A',grouped=True) is original


def test_cross_position_evidence_rejected():
    with pytest.raises(ValueError):code(c(),[dict(position=0,readout='chosen'),dict(position=1,readout='value')],'A',grouped=True)


def test_grouped_cannot_be_used_for_other_banks():
    with pytest.raises(ValueError):code(c(),[dict(position=0,readout='chosen value')],'A')


def test_original_normalization_only():
    assert code(c('Chosen   value'),[dict(position=0,readout='CHOSEN\nvalue')],'A',grouped=True)
    with pytest.raises(ValueError):code(c('chosen value'),[dict(position=0,readout='chosen **value**')],'A',grouped=True)


def test_group_missing_sentinel_preserved():
    x=dict(id='synthetic',category='UNPARSEABLE',values=[],evidence='')
    assert code(x,[dict(position=0,readout='text')],'A',grouped=True) is None


def test_duplicate_positions_rejected():
    with pytest.raises(ValueError):code(c(),[dict(position=0,readout='chosen value')]*2,'A',grouped=True)
