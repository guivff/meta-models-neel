from types import SimpleNamespace
import pytest
from .e107_channel import frozen_wire,decode
P=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global',PROVIDER_NAME='Google')

def call(phase):return dict(id='opaque',phase=phase,rendered=dict(system=None,user='Exact prefix\nExact generic instruction',schema=None))
def saved(end='stop'):return dict(http_status=200,response=dict(model=P.MODEL,provider='Google',usage=dict(cost=.001),choices=[dict(finish_reason=end,message=dict(content='description'))]))

def test_phase_caps_and_exact_messages():
    for phase,n in [('generation',256),('judging',4096)]:
        x=call(phase);w=frozen_wire(x,P)
        assert w['messages']==[dict(role='user',content=x['rendered']['user'])] and w['max_tokens']==n
        assert w['temperature']==0 and w['provider']['zdr'] and not w['provider']['allow_fallbacks']
    x=call('generation');x['rendered']['schema']={}
    with pytest.raises(ValueError):frozen_wire(x,P)

def test_generation_length_retained_judge_length_missing():
    g,_=decode(call('generation'),saved('length'),P)
    assert g['text']=='description' and g['finish_reason']=='length' and g['truncated'] and g['status']=='GENERATED'
    j,_=decode(call('judging'),saved('length'),P)
    assert j['status']=='UNPARSEABLE' and j['reason']=='CHARGED_LENGTH'

def test_unknown_route_error_stops():
    s=saved();s['response']['provider']='wrong'
    with pytest.raises(ValueError):decode(call('generation'),s,P)


def test_judge_refusal_is_recorded_separately():
    s=saved();s['response']['choices'][0]['message']['refusal']='refused'
    result,_=decode(call('judging'),s,P)
    assert result['status']=='REFUSED'
