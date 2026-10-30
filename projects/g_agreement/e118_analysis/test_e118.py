from copy import deepcopy
from types import SimpleNamespace
import pytest
from .adapter import summarize,CONDITIONS,SYSTEM
from projects.g_agreement.understand.blind_judge.internals_c.e118_channel import calls_for,E118Transport,CAP
from projects.g_agreement.understand.blind_judge.internals_c.transport import frozen_wire,decode,check_privacy


def fixture():
    rows=[];terminals=[]
    for c in CONDITIONS:
        for i in range(84):
            ident=('%032x'%len(rows));rows.append(dict(id=ident,item_id=str(i),condition=c,context='The stated place is Cedar.',readout='Cedar is the stated place.',private_target='NEVER_ON_WIRE'))
            terminals.append(dict(id=ident,status='KEPT',result={'verdict':'YES'if i<70 else'NO'}))
    return rows,terminals


def test_blind_prompt_schema_route_and_private_join_exclusion():
    rows,_=fixture();calls=calls_for(rows);p=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global')
    assert len(calls)==252 and all(x['rendered']['system']==SYSTEM for x in calls)
    assert all('NEVER_ON_WIRE'not in str(x)and not any(c in str(x)for c in CONDITIONS)for x in calls)
    wire=frozen_wire(calls[0],p)
    assert wire['max_tokens']==4096 and wire['temperature']==0 and wire['provider']['only']==['google-vertex/global']
    assert wire['provider']['zdr']is True and wire['provider']['data_collection']=='deny'and wire['provider']['allow_fallbacks']is False
    assert calls[0]['rendered']['schema']['schema']['properties']['verdict']['enum']==['YES','NO','OFF-TOPIC']


@pytest.mark.parametrize('fault',['partial','duplicate','wrong_cohort'])
def test_no_subset_duplicate_or_condition_specific_cohort(fault):
    rows,_=fixture()
    if fault=='partial':rows.pop()
    if fault=='duplicate':rows[-1]['id']=rows[0]['id']
    if fault=='wrong_cohort':rows[-1]['item_id']='replacement'
    with pytest.raises(ValueError):calls_for(rows)


def test_exact_common_Wilson_rates_and_registered_threshold():
    from common.stats import wilson
    rows,terminals=fixture();out=summarize(terminals,rows)
    for c in CONDITIONS:
        v=out['conditions'][c];assert v['n_source']==v['n_parseable']==84 and v['n_missing']==0
        assert v['YES']['rate']==wilson(70,84)[0] and v['YES']['ci95']==list(wilson(70,84)[1:])
    assert out['pre_stated_stale_consistency_reading']=='MET'


def test_terminal_missing_not_NO_or_zero_and_no_claim_with_missing_stale():
    rows,terminals=fixture();terminals[0].update(status='UNPARSEABLE',result=None)
    v=summarize(terminals,rows);c=v['conditions'][CONDITIONS[0]]
    assert c['n_parseable']==83 and c['n_missing']==1 and c['counts']['NO']==14 and c['YES']['k']==69
    assert v['pre_stated_stale_consistency_reading']=='NOT EVALUABLE'
    terminals[0]['result']={'verdict':'NO'}
    with pytest.raises(ValueError):summarize(terminals,rows)


def test_all_missing_stays_unknown():
    rows,terminals=fixture()
    for t in terminals:t.update(status='UNPARSEABLE',result=None)
    out=summarize(terminals,rows);assert all(v['YES']['rate']is None and v['YES']['ci95']is None for v in out['conditions'].values())


def test_E118_cap_and_no_E107_privacy_exception():
    assert CAP==1
    for bank,cap in [('E118','2'),('E107','1')]:
        with pytest.raises(ValueError):E118Transport(None,None,dict(bank=bank,allocation_usd=cap),'not_a_credential')
    rows,_=fixture();call=calls_for(rows)[0];p=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global')
    def reject(*args):raise ValueError('private context')
    with pytest.raises(ValueError):check_privacy('E118',call,frozen_wire(call,p),reject,p)
