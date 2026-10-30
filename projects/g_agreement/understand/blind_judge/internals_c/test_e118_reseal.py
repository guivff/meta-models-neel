from pathlib import Path
import pytest
from .e118_reseal import bindings
from projects.g_agreement.readerbench.io import write,sha


def fixture(tmp_path):
    p=tmp_path/'E118_judging/request.response.json';p.parent.mkdir();write(p,{'saved':'unchanged'})
    calls=[dict(id='opaque',phase='judging')]
    rows=[dict(id='opaque',phase='judging',request_id='request',response_sha256=sha(p))]
    audits=[dict(request_id='request',response_sha256=sha(p))]
    return p,calls,rows,audits


def test_actual_frozen_call_phase_wins_over_directory_label(tmp_path):
    p,calls,rows,audits=fixture(tmp_path)
    refs=bindings(rows,calls,audits,tmp_path)
    assert refs==[dict(path=str(p),sha256=sha(p))]
    assert not(tmp_path/'E118_consistency_judging').exists()


def test_partial_or_changed_response_cannot_be_sealed(tmp_path):
    p,calls,rows,audits=fixture(tmp_path)
    with pytest.raises(ValueError):bindings([],calls,audits,tmp_path)
    write(p,{'saved':'changed'})
    with pytest.raises(ValueError):bindings(rows,calls,audits,tmp_path)


def test_wrong_wire_phase_cannot_be_inferred_or_replaced(tmp_path):
    p,calls,rows,audits=fixture(tmp_path);rows[0]['phase']='consistency_judging'
    with pytest.raises(ValueError):bindings(rows,calls,audits,tmp_path)
