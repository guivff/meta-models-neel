import pytest
from .e112_binding import envelope


def test_original_family_code_copied_without_pass_computation_and_missing_preserved():
    code={'expressed':True,'quote':'verbatim'}
    rows=[dict(id='a',status='KEPT',code=code),dict(id='b',status='UNPARSEABLE',code=None)]
    out=envelope(rows,2)
    assert out==[dict(id='a',status='KEPT',result=code),dict(id='b',status='UNPARSEABLE',result=None)]
    assert out[0]['result']is code and rows[1]['code']is None


def test_original_regex_result_envelope_retained():
    code={'pass':False,'instrument':'original'}
    assert envelope([dict(id='a',status='CPU_REGEX',code=code)],1,True)[0]['result']is code


def test_partial_duplicate_or_reinterpreted_null_rejected():
    row=dict(id='a',status='UNPARSEABLE',code=None)
    with pytest.raises(ValueError):envelope([row],2)
    with pytest.raises(ValueError):envelope([row,row],2)
    with pytest.raises(ValueError):envelope([dict(row,code=False)],1)
    with pytest.raises(ValueError):envelope([dict(row,status='CPU_REGEX')],1)
