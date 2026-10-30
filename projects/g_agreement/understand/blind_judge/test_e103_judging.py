from types import SimpleNamespace
from decimal import Decimal
import pytest
from . import e103_judging as e
from .e99_channel import validate_wire_privacy


def test_frozen_plain_prompt_and_e56_settings():
    p=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global')
    x=dict(id='a'*32,prompt='Frozen claim\n\n{exact eight continuations}')
    w=e.wire(x,p)
    assert w['messages']==[dict(role='user',content=x['prompt'])]
    assert w['max_tokens']==4096 and 'response_format' not in w
    assert w['provider']['only']==[p.PROVIDER] and w['provider']['zdr'] and w['provider']['data_collection']=='deny' and not w['provider']['allow_fallbacks']
    with pytest.raises(ValueError):e.wire(dict(x,label=1),p)


def test_exact_yes_no_and_missing():
    assert e.parser(' Yes\n')=='yes' and e.parser('no')=='no'
    for x in ['maybe','yes because...',None,'{"yes":true}']:
        with pytest.raises(ValueError):e.parser(x)


def test_registered_bank_and_global_cap():
    a=dict(packet_receipt_sha256='packet',source_seal_sha256='source')
    r=dict(issuer='integrator',verified=True,bank='E103',reservation_included=True,allocation_usd=5,actual_plus_open_caps_usd=200,**a)
    assert e.budget(r,a)==Decimal(5)
    for change in [dict(allocation_usd=6),dict(actual_plus_open_caps_usd=1001),dict(packet_receipt_sha256='wrong')]:
        with pytest.raises(ValueError):e.budget(dict(r,**change),a)


def test_decode_rendered_json_without_changing_wire():
    from . import funded_queue as f
    from copy import deepcopy
    _,(_,privacy,p,_)=f.route_api()
    frozen=e.frozen_prompt();item=dict(id='a'*32,prompt=frozen['render']('claim',['s:\nA.']*8))
    w=e.wire(item,p);before=deepcopy(w)
    e.privacy_prompt(item,w,privacy.check_wire)
    assert w==before
    item['prompt']=frozen['render']('claim',['C:\\secret\\file']*8)
    with pytest.raises(ValueError):e.privacy_prompt(item,e.wire(item,p),privacy.check_wire)
