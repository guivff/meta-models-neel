from decimal import Decimal
from pathlib import Path
import pytest
from projects.g_agreement.understand.blind_judge import e99_accounting as m


def wire():
    return dict(model=m.MODEL,max_tokens=2,provider=dict(only=[m.PROVIDER],order=[m.PROVIDER],zdr=True,data_collection='deny',allow_fallbacks=False))

def test_separate_cap_and_unresolved_429(tmp_path,monkeypatch):
    root=tmp_path/'e99_40usd';book=m.E99Ledger({'e10_source':'/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/projects/g_agreement/understand/e10'},root)
    book.reserve('request',wire());assert not book.settle_usage('request',{'error':{'code':429}})
    assert Decimal(book.summary()['unresolved_reserve_usd'])>0 and book.summary()['cap_usd']=='40'
    with pytest.raises(ValueError):book.reserve('request',wire())
    assert book.settle_usage('request',{'usage':{'cost':'0.000001'}})
    monkeypatch.setattr(book.api,'upper',lambda w:Decimal('40'))
    with pytest.raises(ValueError):book.reserve('over',wire())
    with pytest.raises(ValueError):m.E99Ledger({'e10_source':'/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/projects/g_agreement/understand/e10'},tmp_path/'e80_e80c_50usd')

def test_refusal_and_failure_distinct():
    body=dict(model=m.MODEL,provider='Google',usage={'cost':.001},choices=[dict(finish_reason='stop',message={})])
    assert m.classify_transport(200,body)['status']=='VALIDATE'
    body['choices'][0]['message']['refusal']='cannot'
    assert m.classify_transport(200,body)['status']=='REFUSED'
    assert m.classify_transport(429,body)==dict(status='FAILED',reason='HTTP_429')
    body['model']='other';assert m.classify_transport(200,body)['reason']=='ROUTE_MISMATCH'

def fixture(n=5):
    calls=[dict(id=str(i),family='hallucination',channel='family',depends_on=[]) for i in range(n)]
    cells=[dict(id='cell'+c['id'],family=c['family'],channel=c['channel'],required_call_ids=[c['id']]) for c in calls]
    terminal=[dict(id=c['id'],status='KEPT') for c in calls]
    return cells,calls,terminal

def test_threshold_and_missing_denominator():
    cells,calls,t=fixture();t[-1]['status']='REFUSED'
    r=m.summarize(cells,calls,t)['families'][0]
    assert r['evaluability']=='ACCOUNTING_THRESHOLD_PASSED' and r['refused_cells']==1
    r=m.summarize(cells,calls,t[:-2])['families'][0]
    assert r['unjudged_cells']==2 and r['evaluability']=='NOT EVALUABLE' and r['cells']==5

def test_two_stage_and_corroboration_separate():
    cells,calls,t=fixture(1)
    calls.append(dict(id='stageB',family='hallucination',channel='family',depends_on=['0']))
    cells[0]['required_call_ids']=['stageB'];t[0]['status']='FAILED';t.append(dict(id='stageB',status='KEPT'))
    calls.append(dict(id='corr',family='hallucination',channel='corroboration',depends_on=[]))
    cells.append(dict(id='corr-cell',family='hallucination',channel='corroboration',required_call_ids=['corr']))
    t.append(dict(id='corr',status='KEPT'))
    results={r['channel']:r for r in m.summarize(cells,calls,t)['families']}
    assert results['family']['judged']==0 and results['corroboration']['judged']==1
    calls[0]['depends_on']=['stageB']
    with pytest.raises(ValueError):m.summarize(cells,calls,t)

def test_wire_unchanged_and_terminal_validation():
    from types import SimpleNamespace
    from projects.g_agreement.understand.blind_judge.e99_channel import frozen_wire,terminal_record
    rendered=dict(system='Exact system\n',user='Exact user\n  spacing',schema=dict(name='fixture',strict=True,schema=dict(type='object',additionalProperties=False,required=['ok'],properties={'ok':{'type':'boolean'}})))
    w=frozen_wire(rendered,SimpleNamespace(MODEL=m.MODEL,PROVIDER=m.PROVIDER))
    assert w['messages'][0]['content']==rendered['system'] and w['messages'][1]['content']==rendered['user']
    body=dict(model=m.MODEL,provider='Google',usage={'cost':.001},choices=[dict(finish_reason='stop',message={'content':'{"ok":true}'})])
    assert terminal_record('call',200,body,rendered)['status']=='KEPT'
    body['choices'][0]['message']['content']='{"ok":"true"}'
    assert terminal_record('call',200,body,rendered)['status']=='UNPARSEABLE'

def test_headline_truth_inventory_blinding():
    from projects.g_agreement.understand.blind_judge.e99_headline import load_frozen,claim_inventory,wrong_spans
    h,c=load_frozen();text='The door is open. The sky is blue. A disputed result.'
    first={'samples':[dict(idx=0,kind='specific',spans=[dict(type='wrong',text='The door is open.',why='fixture')],rationale='')]}
    second={'samples':[dict(idx=0,kind='specific',claims=[dict(quote='door is open',status='true',why=''),dict(quote='The sky is blue.',status='true',why=''),dict(quote='A disputed result.',status='disputed',why=''),dict(quote='invented quote',status='true',why='')],rationale='')]}
    public,private,counts=claim_inventory(first,second,text)
    assert len(public)==2 and counts==dict(false=1,true=1,unverifiable=1,disputed=1,off_topic=0,n_unverified=1)
    assert all(set(p)=={'claim_id','quote'} for p in public)
    assert [p['status'] for p in private]==['false','true']
    rendered=c.render(text,'The sky is blue.',public)
    assert 'status' not in rendered['user'] and 'false' not in rendered['user']
    assert 'Established FALSE spans' in h.render(dict(prompt='Q',response='abc'),dict(char=1),text,wrong_spans=wrong_spans(first,text))['user']
    with pytest.raises(ValueError):claim_inventory(first,{'samples':[]},text)


def test_transport_validation_retries_reserved_separately(tmp_path,monkeypatch):
    from projects.g_agreement.understand.blind_judge.e99_transport import E99Transport
    from projects.g_agreement.understand.blind_judge.run import route_modules
    t=E99Transport.__new__(E99Transport)
    t.api,t.privacy,t.protocol,t.io=route_modules({'e10_source':'/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/projects/g_agreement/understand/e10'})
    t.api.CAP=Decimal('40');t.root=tmp_path/'e99_40usd'
    t.saved=(t.protocol.payload,t.protocol.validate,t.privacy.check_wire,t.io.digest)
    n=[]
    def send(w):
        n.append(w)
        value='{"ok":"invalid"}' if len(n)==1 else '{"ok":true}'
        return 200,dict(model=m.MODEL,provider='Google',usage={'cost':.001},choices=[dict(finish_reason='stop',message={'content':value})])
    t.client=t.api.Client(t.root,'unused',send=send)
    rendered=dict(system='fixture',user='fixture',schema=dict(name='fixture',strict=True,schema=dict(type='object',additionalProperties=False,required=['ok'],properties={'ok':{'type':'boolean'}})))
    try:
        result=t.call('a'*32,rendered)
        assert result['status']=='KEPT' and len(n)==2 and n[0]==n[1]
        assert len(t.client.ledger.totals()[0])==2
        assert [a['status'] for a in result['attempt_history']]==['UNPARSEABLE','KEPT']
        t.call('a'*32,rendered);assert len(n)==2
    finally:
        t.protocol.payload,t.protocol.validate,t.privacy.check_wire,t.io.digest=t.saved

def test_agentic_plain_text_and_source_refusal_accounting():
    from .e99_families import Renderers
    from .e99_channel import frozen_wire,terminal_record
    from types import SimpleNamespace
    r=Renderers();rendered=r.render('agentic_misalignment','position',readouts_by_layer={44:'a note'})
    w=frozen_wire(rendered,SimpleNamespace(MODEL=m.MODEL,PROVIDER=m.PROVIDER))
    assert w['messages']==[dict(role='user',content=rendered['user'])] and 'response_format' not in w
    body=dict(model=m.MODEL,provider='Google',usage={'cost':.001},choices=[dict(finish_reason='stop',message={'content':'uninformative'})])
    assert terminal_record('a',200,body,rendered)['result']=='uninformative'
    chunks=r.agentic_notes({1:dict(status='REFUSED'),2:dict(status='KEPT',result='uninformative'),3:dict(status='KEPT',result='a plan')})
    assert chunks==[[(1,'(positions 1-2 uninformative)'),(3,'a plan')]]
    with pytest.raises(ValueError):r.agentic_notes({1:dict(status='FAILED')})
    parsed=r.parse_design('{"identified_family":"none", "design_rank":9,"origin_claimed":"unstated","origin_actual":"unstated"}')
    assert parsed['design_rank']==3
    with pytest.raises(ValueError):r.parse_design('unparseable')
    calls=[dict(id='a',family='agentic_misalignment',channel='family',stage='position',depends_on=[])]
    cells=[dict(id='c',family='agentic_misalignment',channel='family',required_call_ids=['a'])]
    t=[dict(id='a',status='REFUSED',source_refusal_uninformative=True)]
    counts=m.summarize(cells,calls,t)['families'][0]
    assert counts['judged']==1 and counts['refused_cells']==1
