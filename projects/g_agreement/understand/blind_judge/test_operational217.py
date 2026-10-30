from types import SimpleNamespace
from copy import deepcopy
import pytest
from .operational217 import audit_response,truncated,judge,adapt


def test_charged_length_no_retry_and_missing():
    xs=[dict(id='opaque')];calls=[]
    terminal=judge(xs,lambda batch,n:(calls.append(n) or truncated(batch)))
    flat,audit=adapt(terminal,xs)
    assert calls==[0] and flat[0]['category']=='UNPARSEABLE'
    assert audit[0]['attempts']==0 and audit[0]['terminal_reason']=='CHARGED_LENGTH'


def test_length_route_and_known_cost_still_required():
    p=SimpleNamespace(PROVIDER_NAME='Google',MODEL='google/gemini-3.1-flash-lite')
    saved=dict(http_status=200,response=dict(provider=p.PROVIDER_NAME,model=p.MODEL,usage=dict(cost=.001),choices=[dict(finish_reason='length')]))
    before=deepcopy(saved);assert audit_response(saved,p)['terminal_unparseable'] is True
    assert saved==before
    saved['response']['provider']='wrong'
    with pytest.raises(ValueError):audit_response(saved,p)


def test_unknown_finish_stops():
    p=SimpleNamespace(PROVIDER_NAME='Google',MODEL='model')
    saved=dict(http_status=200,response=dict(provider='Google',model='model',usage=dict(cost=0),choices=[dict(finish_reason='unknown')]))
    with pytest.raises(ValueError):audit_response(saved,p)
