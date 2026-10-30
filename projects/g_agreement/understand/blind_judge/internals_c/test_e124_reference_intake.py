import pytest
from .e124_reference_intake import project


def test_source_cohort_and_id_join_cannot_be_replaced_by_condition_or_order():
    ro=[dict(id='b',readout='B'),dict(id='a',readout='A'),dict(id='c',readout='C')]
    refs=[dict(id='a',condition='E82_belief_wrong',cohort='belief_wrong',reference_text='refa'),dict(id='b',condition='E82_belief_wrong',cohort='no_canonical_truth',reference_text='refb'),dict(id='c',condition='E104_U_44_random',reference_text='refc')]
    u,p,e=project(ro,refs,lambda x:x)
    assert u==[dict(id='a',model_reference='refa',readout='A'),dict(id='c',model_reference='refc',readout='C')]
    assert e==['b']
    with pytest.raises(ValueError):project(ro[:-1],refs,lambda x:x)
    refs[1]['cohort']='unknown'
    with pytest.raises(ValueError):project(ro,refs,lambda x:x)


def test_missing_reference_and_duplicate_custody_fail_before_any_call():
    ro=[dict(id='a',readout='')];refs=[dict(id='a',condition='E104_U_44_steered',reference_text='r')]
    assert project(ro,refs,lambda x:'literal')[0][0]['readout']==''
    with pytest.raises(ValueError):project(ro,refs,lambda x:None)
    with pytest.raises(ValueError):project(ro+ro,refs+refs,lambda x:'literal')
