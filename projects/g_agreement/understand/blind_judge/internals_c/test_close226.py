import pytest
from .close226 import terminal_refs


def test_original_code_pointer_and_separate_missing_sentinel_keep_null():
    rows=[dict(id='a',kind='original57',status='KEPT',code=dict(id='a')),
          dict(id='b',kind='original57',status='UNPARSEABLE',code=None),
          dict(id='c',kind='eval85',status='UNPARSEABLE',code=None)]
    refs,missing=terminal_refs(rows,3,dict(seal='original',sha256='hash'))
    assert rows[1]['code']is None and refs[0]['original_code']['keys']==[0,'code']
    assert len(missing)==1 and missing[0]['code']==dict(id='b',category='UNPARSEABLE',values=[],evidence='')
    assert'missing_sentinel_index'not in refs[2]


def test_partial_duplicate_or_nonkept_code_cannot_be_closed():
    row=dict(id='a',kind='value',status='UNPARSEABLE',code=None);src=dict(seal='original',sha256='hash')
    with pytest.raises(ValueError):terminal_refs([row],2,src)
    with pytest.raises(ValueError):terminal_refs([row,row],2,src)
    with pytest.raises(ValueError):terminal_refs([dict(row,code=False)],1,src)
