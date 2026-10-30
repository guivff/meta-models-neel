import pytest
from .consistency_close import terminal_refs
from .seal_bank import disposition


def test_original_null_terminal_pointer_never_becomes_no_or_zero():
    row=dict(id='x',status='UNPARSEABLE',result=None)
    assert terminal_refs([row],'seal','sha',1)[0]['terminal']['keys']==[0]
    with pytest.raises(ValueError):terminal_refs([row],'seal','sha',2)
    with pytest.raises(ValueError):terminal_refs([dict(row,result={'verdict':'NO'})],'seal','sha',1)


def test_combined_cost_cannot_release_unknown_or_raise_original_cap():
    assert disposition(1,'.827057',0)['unused_allocation_released_usd']=='0.172943'
    with pytest.raises(ValueError):disposition(1,'.827057','.001')
    with pytest.raises(ValueError):disposition(1,'1.000001',0)
