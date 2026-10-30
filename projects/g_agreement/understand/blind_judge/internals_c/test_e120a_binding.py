from copy import deepcopy
import pytest
from .e120a_binding import assemble


def test_shuffled_dispatch_identity_binds_code_and_id_siblings_including_null():
    native=dict(seal='native',sha256='hash')
    joins=[dict(id='a',item_id='itemA',block=52,source_ref=dict(native,member='jobs/x.json',keys=[0,'text'])),dict(id='b',item_id='itemB',block=60,source_ref=dict(native,member='jobs/x.json',keys=[1,'text']))]
    original={'original_code':'no injected id'}
    rows=[dict(id='b',kind='eval85',status='UNPARSEABLE',code=None),dict(id='a',kind='eval85',status='KEPT',code=original)]
    projected=assemble(joins,rows,native,2)
    assert projected[0]['fields']['code']['keys']==[1,'code']
    assert projected[1]['fields']['judgment_id']['keys']==[0,'id']
    assert rows[1]['code'] is original and 'id' not in original
    wrong=deepcopy(joins);wrong[0]['source_ref']['sha256']='different'
    with pytest.raises(ValueError):assemble(wrong,rows,native,2)
    with pytest.raises(ValueError):assemble(joins,rows[:1],native,2)
