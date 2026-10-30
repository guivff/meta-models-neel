import pytest
from .e120a_close import pointers
from .seal_bank import disposition

def test_literal_null_and_direct_source_pointer_no_id_insertion():
    rows=[dict(id='x',kind='eval85',status='UNPARSEABLE',code=None)]
    refs=pointers(rows,'original','hash',1)
    assert refs[0]['original_code']['keys']==[0,'code']
    with pytest.raises(ValueError):pointers(rows,'original','hash',2)
    with pytest.raises(ValueError):pointers([dict(rows[0],code={})],'original','hash',1)

def test_combined_actual_includes_original_c_and_never_releases_unknown():
    assert disposition(2,'.89204125',0)['unused_allocation_released_usd']=='1.10795875'
    with pytest.raises(ValueError):disposition(2,'.89204125','.001')
    with pytest.raises(ValueError):disposition(2,'2.00001',0)
