import pytest
from projects.g_agreement.understand.e13.claude_analysis import kappa,accuracy


def test_kappa_known_confusion():
    a=['A','A','B','B'];b=['A','A','A','B']
    assert kappa(a,b)['agreement']==.75
    assert kappa(a,b)['kappa']==.5


def test_kappa_degenerate_is_not_zero():
    assert kappa([],[])['kappa'] is None
    assert kappa(['A'],['A'])['kappa'] is None
    with pytest.raises(ValueError):kappa(['A'],[])


def test_unclear_denominator_and_truth_balance():
    r=[dict(mentions=True,value='A',truth='A'),dict(mentions=True,value='unclear',truth='B'),dict(mentions=False,value=None,truth='B')]
    m=accuracy(r,'mentions','value')
    assert m['occurrence']['k']==2 and m['occurrence']['n']==3
    assert m['correct_among_occurrences']['rate']==.5
    assert m['correct_among_resolved']['rate']==1
    assert m['unresolved']==1 and m['majority_truth_baseline']==1


def test_no_enact_is_unavailable():
    m=accuracy([dict(enacts=False,enact_value=None,truth='B')],'enacts','enact_value')
    assert m['occurrence']['rate']==0
    assert m['correct_among_occurrences']['rate'] is None
    assert m['correct_among_resolved']['rate'] is None
