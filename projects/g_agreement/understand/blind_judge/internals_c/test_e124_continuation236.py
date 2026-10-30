from copy import deepcopy
from types import SimpleNamespace
import hashlib
import pytest
from . import e124_continuation236 as c


def test_dense_original_prefix_recovered_by_id_without_order_or_reclassification():
    calls=[dict(id=x)for x in ('a','b','c')];ts=[dict(id='b',status='UNPARSEABLE',result=None),dict(id='a',status='KEPT',result={'label':'YES'})]
    before=deepcopy(ts);out=c.dense_prefix(calls,ts)
    assert [x['id']for x in out]==['a','b'] and ts==before and out[0] is ts[1] and out[1]['result'] is None


@pytest.mark.parametrize('fault',['gap','foreign','duplicate','unknown_status'])
def test_incomplete_or_duplicate_cached_identity_is_not_guessed(fault):
    calls=[dict(id=x)for x in ('a','b','c')];ts=[dict(id='a',status='KEPT')]
    if fault=='gap':ts.append(dict(id='c',status='KEPT'))
    elif fault=='foreign':ts.append(dict(id='other',status='KEPT'))
    elif fault=='duplicate':ts.append(dict(ts[0]))
    else:ts[0]['status']='MISSING'
    with pytest.raises(ValueError):c.dense_prefix(calls,ts)


def test_original_request_salt_and_legacy_rate_cache_identity_only():
    call=dict(id='opaque',phase='judging');wire=dict(content='blind text');input_sha='input'
    base=hashlib.sha256(('WIC:E124_judging:input:opaque:'+c.transport.canonical(wire)).encode()).hexdigest()
    c.request_identity(input_sha,call,wire,base)
    c.request_identity(input_sha,call,wire,hashlib.sha256(('RATE429:'+base+':4').encode()).hexdigest())
    with pytest.raises(ValueError):c.request_identity('changed',call,wire,base)


def test_extended_deadline_cap_unchanged_and_no_unpriced_rate_retry(monkeypatch):
    monkeypatch.setattr(c.e124_channel,'source_gate',lambda:None);expiry=c.transport.EXPIRY;rate=c.parallel_funded.MAX_429_RETRIES;caps=dict(c.transport.CAPS)
    with pytest.raises(RuntimeError):
        with c.worker():
            assert c.transport.EXPIRY==1793372400 and c.parallel_funded.MAX_429_RETRIES==0 and c.transport.CAPS['E124']==3
            raise RuntimeError('restore')
    assert c.transport.EXPIRY==expiry and c.parallel_funded.MAX_429_RETRIES==rate and c.transport.CAPS==caps


def test_extended_cutoff_is_rechecked_at_post_after_shared_pacing(monkeypatch):
    sent=[];req=SimpleNamespace(post=lambda *a,**k:sent.append(a));obj=object.__new__(c.ContinuationTransport);obj.api=SimpleNamespace(requests=req)
    monkeypatch.setattr(c.e124_channel.E124Transport,'__enter__',lambda self:self);monkeypatch.setattr(c.e124_channel.E124Transport,'__exit__',lambda self,*a:None)
    obj.__enter__()
    def ended():raise ValueError('deadline expired')
    monkeypatch.setattr(c.transport,'unpaused',ended)
    with pytest.raises(ValueError):req.post('https://openrouter.ai/api/v1/chat/completions')
    assert not sent;obj.__exit__(None,None,None)


def test_failure_is_visible_to_existing_publication_watcher(tmp_path):
    c.record_stop(tmp_path,ValueError('no charge guessed'))
    assert c.read(tmp_path/'STATUS.json')['status']=='STOPPED'
    assert c.read(tmp_path/'CONTINUATION236_STOPPED.json')['no_resend'] is True
    assert not(tmp_path/'JUDGMENT_SEAL.json').exists()
