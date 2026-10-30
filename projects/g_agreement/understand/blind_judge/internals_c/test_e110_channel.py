from types import SimpleNamespace
import copy
import pytest
from . import e110_channel as c
from .transport import frozen_wire, check_privacy
from .registered import unit_call


def fixture(n=60):
    items=[];native=[];generated=[]
    for i in range(n):
        ident=str(i);values={'A':['belief entity'],'B':['true entity']};letters={'belief':'A','truth':'B'}
        items.append(dict(id=ident,cohort='belief_wrong',prompt='A public question?',property='intermediate entity',
            values_by_system={s:copy.deepcopy(values) for s in c.SYSTEMS},target_letters_by_system={s:dict(letters) for s in c.SYSTEMS}))
        for s in ('oracle','nla'):native.append(dict(item_id=ident,reader=s,layer=44 if s=='oracle'else 42,text='belief entity',source_ref=dict(member='batch',keys=[i,'text'])))
        generated.append(dict(id=c.opaque('E110','outside',ident),phase='generation',status='GENERATED',finish_reason='length'if i==0 else'stop',text='An outside description.',refusal=None))
    return dict(experiment='E110',deviation=2,labels_cpu_only=True,all_selected_survivors_retained=True,original_TwoHopFact_reused=False,
        E82_reference_rejudged=False,items=items,survivor_counts={'belief_wrong':n},selection_mode='stable belief'),native,generated


def test_variable_roster_original_letter_maps_and_whole_three_system_grid():
    source,native,generated=fixture(84)
    x=source['items'][0];x['values_by_system']['nla']={'B':['belief entity'],'A':['true entity']};x['target_letters_by_system']['nla']={'belief':'B','truth':'A'}
    units,joins=c.make_units(source,native,generated)
    assert len(units)==315 and len(joins)==252
    assert joins[1]['target_letters']['belief']=='B' and units[1]['data']['values']['B']==['belief entity']
    assert all('cohort'not in u['data'] and 'reader'not in u['data'] for u in units)
    c.check_scope('E110',units,dict(experiment='E110',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,selected_items=84))


def test_exact_E107_outside_and_E82_judging_wire_settings():
    source,native,generated=fixture();p=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global')
    call=c.outside_calls(source)[0];wire=frozen_wire(call,p)
    assert wire['messages']==[dict(role='user',content='A public question?\n'+c.INSTRUCTION)]
    assert wire['temperature']==0 and wire['max_tokens']==256 and 'response_format'not in wire
    assert wire['provider']['only']==['google-vertex/global'] and wire['provider']['zdr']is True
    assert wire['provider']['data_collection']=='deny' and wire['provider']['allow_fallbacks']is False
    units,_=c.make_units(source,native,generated);judge,_=unit_call(units[0],p);j=frozen_wire(judge,p)
    assert units[0]['rubric']==c.amended().decode() and j['max_tokens']==4096 and j['temperature']==0


@pytest.mark.parametrize('fault',['partial_native','partial_generation','old_reference','missing_truth','wrong_map','floor'])
def test_no_partial_old_or_unbound_source(fault):
    source,native,generated=fixture()
    if fault=='partial_native':native.pop()
    if fault=='partial_generation':generated.pop()
    if fault=='old_reference':source['E82_reference_rejudged']=True
    if fault=='missing_truth':source['items'][0]['values_by_system']['oracle']['B']=[]
    if fault=='wrong_map':source['items'][0]['target_letters_by_system']['outside']={'belief':'B','truth':'A'}
    if fault=='floor':source['items'].pop();source['survivor_counts']['belief_wrong']=59
    with pytest.raises(ValueError):c.make_units(source,native,generated)


def test_no_E107_privacy_exception_for_E110():
    source,_,_=fixture();p=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global');call=c.outside_calls(source)[0]
    def reject(*unused):raise ValueError('private source')
    with pytest.raises(ValueError):check_privacy('E110',call,frozen_wire(call,p),reject,p)


def test_cap_and_module_import_have_no_canonical_allocation_or_calls():
    assert c.CAP==10 and 'E110'not in c.transport.CAPS
    for bank,cap in [('E110','11'),('E110','9'),('E107','10')]:
        with pytest.raises(ValueError):c.E110Transport(None,None,dict(bank=bank,allocation_usd=cap),'not_a_credential')
