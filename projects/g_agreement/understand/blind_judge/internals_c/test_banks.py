import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from . import banks as b, transport as t

P=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global',PROVIDER_NAME='Google')


def call(phase='generation'):
    return dict(id='a'*32,phase=phase,rendered=dict(system=None,user='exact frozen text',schema=None))


def saved(finish='stop'):
    return dict(http_status=200,response=dict(model=P.MODEL,provider='Google',usage=dict(cost=.001),
            choices=[dict(finish_reason=finish,message=dict(content='description'))]))


def test_combined_caps_exact_route_and_phase_settings():
    assert {k:str(v) for k,v in t.CAPS.items()}==dict(E107='15',E108='8',E109='6',E85='2',E106='15')
    for phase,n in [('generation',256),('extraction',4096),('judging',4096),('original',4096)]:
        wire=t.frozen_wire(call(phase),P)
        assert wire['messages']==[dict(role='user',content='exact frozen text')]
        assert wire['max_tokens']==n and wire['temperature']==0
        assert wire['provider']['only']==[P.PROVIDER] and wire['provider']['order']==[P.PROVIDER]
        assert wire['provider']['zdr'] is True and wire['provider']['data_collection']=='deny'
        assert wire['provider']['allow_fallbacks'] is False


@pytest.mark.parametrize('field,value',[('truth','A'),('label',1),('reader','oracle'),('private_join',{})])
def test_private_metadata_rejected_before_wire(field,value):
    c=call();c[field]=value
    with pytest.raises(ValueError):t.frozen_wire(c,P)


def test_generation_length_preserved_judge_length_terminal_no_validator():
    g,_=t.decode(call(),saved('length'),P)
    assert g['text']=='description' and g['truncated'] and g['finish_reason']=='length'
    def forbidden(v):raise AssertionError('must not parse a charged truncation')
    for phase in ('extraction','judging','original'):
        r,_=t.decode(call(phase),saved('length'),P,forbidden)
        assert r['status']=='UNPARSEABLE' and r['reason']=='CHARGED_LENGTH'


@pytest.mark.parametrize('field,value',[('provider','unknown'),('model','another/model')])
def test_wrong_response_route_stops(field,value):
    s=saved();s['response'][field]=value
    with pytest.raises(ValueError):t.decode(call(),s,P)


def test_unknown_finish_and_unknown_cost_stop():
    for s in [saved('unknown'),saved()]:
        if s['response']['choices'][0]['finish_reason']=='stop':s['response'].pop('usage')
        with pytest.raises((ValueError,TypeError)):t.decode(call(),s,P)


def test_402_writes_both_shared_latches(tmp_path,monkeypatch):
    monkeypatch.setattr(t,'SHARED',tmp_path/'funded')
    monkeypatch.setattr(t,'ACCOUNT_PAUSE',tmp_path/'account.json')
    p=tmp_path/'402.json';p.write_text('{}')
    with pytest.raises(t.funded.CreditPause):t.pause('E108',p)
    assert (t.SHARED/'PAUSED_402.json').exists() and t.ACCOUNT_PAUSE.exists()
    with pytest.raises(ValueError):t.unpaused()
    (t.SHARED/'PAUSED_402.json').unlink()
    with pytest.raises(ValueError):t.unpaused()
    t.write(t.ACCOUNT_PAUSE,dict(status='FUNDING_CONFIRMED_RESUMED'))
    t.unpaused()


def test_exact_five_exception_rejects_any_wire_mutation(monkeypatch):
    c=call();c['rendered']['user']='literal benchmark /etc/config'
    wire=t.frozen_wire(c,P)
    pair=dict(source_user_utf8_sha256=hashlib.sha256(c['rendered']['user'].encode()).hexdigest(),
              full_frozen_wire_sha256=hashlib.sha256(t.canonical(wire).encode()).hexdigest())
    monkeypatch.setattr(t,'sha',lambda p:'proposalhash')
    monkeypatch.setattr(t,'read',lambda p:dict(issuer='Guiv',answer='Approve only these five exact hash pairs',proposal_sha256='proposalhash') if 'APPROVAL' in str(p) else dict(exact_entries=[pair]))
    def guard(*args):raise ValueError('path')
    t.check_privacy('E107',c,wire,guard,P)
    for key,value in [('model','other'),('max_tokens',257),('temperature',1)]:
        wrong=copy.deepcopy(wire);wrong[key]=value
        with pytest.raises(ValueError):t.check_privacy('E107',c,wrong,guard,P)
    wrong=copy.deepcopy(c);wrong['rendered']['user']+=' '
    with pytest.raises(ValueError):t.check_privacy('E107',wrong,t.frozen_wire(wrong,P),guard,P)
    for bank in ('E108','E109','E85','E106'):
        with pytest.raises(ValueError):t.check_privacy(bank,c,wire,guard,P)


@pytest.mark.parametrize('text',['/Users/somebody/private', '.'.join(str(n) for n in range(1,5))+':443','sk-or-v1-'+('x'*24)])
def test_sensitive_patterns_retained_even_in_approved_hash_fixture(text,monkeypatch):
    c=call();c['rendered']['user']=text;wire=t.frozen_wire(c,P)
    pair=dict(source_user_utf8_sha256=hashlib.sha256(text.encode()).hexdigest(),full_frozen_wire_sha256=hashlib.sha256(t.canonical(wire).encode()).hexdigest())
    monkeypatch.setattr(t,'sha',lambda p:'h')
    monkeypatch.setattr(t,'read',lambda p:dict(issuer='Guiv',answer='Approve only these five exact hash pairs',proposal_sha256='h') if 'APPROVAL' in str(p) else dict(exact_entries=[pair]))
    def guard(*a):raise ValueError('pattern')
    with pytest.raises(ValueError):t.check_privacy('E107',c,wire,guard,P)


def test_outside108_exact_registered_question_no_metadata():
    item=dict(id='a'*32,prompt='Name one animal:')
    meta=dict(id=item['id'],kind='native',category='animal',arm='immediate',prompt_id='private')
    c=b.outside108(item,meta)
    assert c['rendered']==dict(system=None,user='Name one animal:\nWhich animal will this model most likely choose? Answer with one word.',schema=None)
    assert 'private' not in c['rendered']['user']


def test_choice_extraction_none_multiple_and_duplicate_ids():
    xs=[dict(id='a'*32,category='animal',continuation='I chose a dog.')]
    c,v=b.choice108(xs,'extraction')
    assert 'readout' not in json.loads(c['rendered']['user'])[0]
    v(dict(records=[dict(id=xs[0]['id'],status='ONE',canonical_member='dog',evidence='dog')]))
    for status in ('NONE','MULTIPLE'):
        v(dict(records=[dict(id=xs[0]['id'],status=status,canonical_member='',evidence='')]))
    with pytest.raises(ValueError):v(dict(records=[dict(id=xs[0]['id'],status='ONE',canonical_member='cat',evidence='cat')]))
    row=dict(id=xs[0]['id'],status='NONE',canonical_member='',evidence='')
    with pytest.raises(ValueError):v(dict(records=[row,row]))


def test_e108_readout_hit_evidence_and_forbidden_truth_metadata():
    xs=[dict(id='a'*32,chosen_member='dog',readout='The choice is a dog.')]
    _,v=b.choice108(xs,'judging')
    v(dict(records=[dict(id=xs[0]['id'],hit=True,evidence='dog')]))
    v(dict(records=[dict(id=xs[0]['id'],hit=False,evidence='')]))
    with pytest.raises(ValueError):v(dict(records=[dict(id=xs[0]['id'],hit=True,evidence='cat')]))
    xs[0]['true_label']=1
    with pytest.raises(ValueError):b.choice108(xs,'judging')


def test_placebo106_any_trained_value_no_binary_assignment():
    values=dict(nesting_depth=['one','two'],indent_level=['one','four'],page_range_digit=['2','3'])
    xs=[dict(id='a'*32,readout='The indentation is four.')]
    c,v=b.placebo106(xs,values)
    assert json.loads(c['rendered']['user'])['trained_values']==values
    assert 'target' not in json.loads(c['rendered']['user'])
    v(dict(records=[dict(id=xs[0]['id'],states_any_trained_value=True,evidence='indentation is four')]))
    with pytest.raises(ValueError):v(dict(records=[dict(id=xs[0]['id'],states_any_trained_value=False,evidence='four')]))
    with pytest.raises(ValueError):b.placebo106(xs,{'nesting_depth':['one']})


def test_e85_frozen_wording_and_independent_primary():
    item=dict(id='a'*32,source_text='A test-suite README',readout='This is a benchmark document.')
    c,v=b.eval85(item)
    assert c['rendered']['system']==b.load_judge85().SYSTEM
    code=dict(a_model_self_evaluated=False,b_evaluation_genre_vocabulary=True,c_absent_genre_named=False,
              a_evidence='',b_evidence='benchmark',c_genres=[],c_evidence='')
    v(code)
    bad=dict(code,a_model_self_evaluated=True)
    with pytest.raises(ValueError):v(bad)
