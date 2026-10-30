import pytest
from . import authority236 as a
from . import transport
from projects.g_agreement.readerbench.io import write,sha


def receipt():
    return dict(authority='direct Guiv paid-judging extension',paid_until_epoch=a.EXTENDED_EXPIRY,no_new_runs=True,bank_caps_unchanged=True,missing_stays_missing=True,route=dict(model='google/gemini-3.1-flash-lite',provider='google-vertex/global',gateway='OpenRouter',zdr=True,data_collection='deny',fallbacks=False),existing_source_sha256={'E118':['frozen']})


def test_new_deadline_is_strict_and_no_scope_or_route_extension():
    v=receipt();a.validate(v,'E118','frozen',a.EXTENDED_EXPIRY-1)
    for bank,source,now in [('E118','frozen',a.EXTENDED_EXPIRY),('E118','new',0),('E999','frozen',0)]:
        with pytest.raises(ValueError):a.validate(v,bank,source,now)
    v['route']['fallbacks']=True
    with pytest.raises(ValueError):a.validate(v,'E118','frozen',0)


def test_process_local_cutoff_restored_and_all_pause_checks_retained(tmp_path,monkeypatch):
    monkeypatch.setattr(transport,'HERE',tmp_path);monkeypatch.setattr(transport,'ROOT',tmp_path)
    write(tmp_path/'PAID_AUTHORITY_EXTENSION236.json',receipt())
    write(tmp_path/'PAID_AUTHORITY_EXTENSION236_SOURCE_SEAL.json',dict(files={'PAID_AUTHORITY_EXTENSION236.json':sha(tmp_path/'PAID_AUTHORITY_EXTENSION236.json')}))
    original=transport.EXPIRY
    with pytest.raises(RuntimeError):
        with a.existing_work('E118','frozen'):
            assert transport.EXPIRY==a.EXTENDED_EXPIRY
            raise RuntimeError('exit')
    assert transport.EXPIRY==original
