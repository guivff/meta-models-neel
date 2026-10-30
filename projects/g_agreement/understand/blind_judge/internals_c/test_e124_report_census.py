import pytest
from .e124_report_census import classification


def test_original_target_letter_and_missing_cannot_be_replaced_by_false():
    c=dict(id='x',source_set='E118b',family='wrong_bridge',item_id='source',position=7,original_label_refs={'belief':dict(target_letter='B')})
    r=dict(id='x',condition='E82_belief_wrong',cohort='belief_wrong')
    assert classification(c,r,lambda p:None)['belief_stating'] is None
    assert classification(c,r,lambda p:dict(category='states_value',values=['B']))['belief_stating'] is True
    assert classification(c,r,lambda p:dict(category='states_value',values=['A']))['belief_stating'] is False
    assert classification(c,r,lambda p:dict(category='states_value',values=['A','B']))['belief_stating'] is True


def test_reference_condition_and_item_identity_checked_before_copy():
    c=dict(id='a',source_set='E118a',condition='E104_U_44_steered')
    assert classification(c,dict(id='a',condition=c['condition']),lambda p:None)==dict(id='a',condition=c['condition'])
    with pytest.raises(ValueError):classification(c,dict(id='b',condition=c['condition']),lambda p:None)
    with pytest.raises(ValueError):classification(c,dict(id='a',condition='E109_52_steered'),lambda p:None)
