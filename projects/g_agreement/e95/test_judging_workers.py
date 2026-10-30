import json
import os
import time
from decimal import Decimal

import pytest

from projects.g_agreement.e95.judging_workers import parallel_judge
from projects.g_agreement.understand.blind_judge.operational217 import judge
from projects.g_agreement.readerbench.io import read, write


def fixture_send(batch, attempt):
    time.sleep(.01)
    return [dict(id=x['id'],status='INVALID' if x['id']=='3' and attempt==0 else 'KEPT',
                 code=dict(worker_pid=os.getpid())) for x in batch]


def test_spawn_workers_keep_original_order_and_run_schema_retries_only_for_invalid():
    items = [dict(id=str(i)) for i in range(8)]
    result = parallel_judge(items, fixture_send, judge)
    assert [r['id'] for r in result] == [x['id'] for x in items]
    assert len({r['code']['worker_pid'] for r in result}) == 2
    assert all(r['code']['worker_pid'] != os.getpid() for r in result)
    assert result[3]['attempts'] == 1
    assert all(r['attempts']==0 for i,r in enumerate(result) if i!=3)


@pytest.mark.parametrize('reason', ['RATE_LIMIT_EXHAUSTED', 'UNCHARGED_BACKEND_RETRIES_EXHAUSTED','UNKNOWN_REQUEST_NO_REPLAY'])
def test_exhausted_backend_stays_missing_without_new_schema_send(reason):
    calls=[]
    def send(items, attempt):
        calls.append(attempt)
        return [dict(id=x['id'], status='UNPARSEABLE', code=None, terminal_reason=reason) for x in items]
    result=judge([dict(id='a')],send)
    assert calls==[0] and result[0]['code'] is None and result[0]['status']=='UNPARSEABLE'


def test_real_e10_ledger_books_429_reserved_upper_and_retains_exact_e87_wire(monkeypatch,tmp_path):
    from projects.g_agreement.e95 import judging_workers as workers
    from projects.g_agreement.understand.blind_judge import e87
    from projects.g_agreement.understand.blind_judge.run import ROOT,route_modules
    from projects.g_agreement.understand.blind_judge.validator221 import e87_classify
    api,privacy,protocol,io=route_modules(read(ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'))
    monkeypatch.setattr(api,'CAP',Decimal(60))
    monkeypatch.setattr(workers,'claim_slot',lambda *a:None)
    monkeypatch.setattr(workers.transport,'unpaused',lambda:None)
    real_action=workers.retry_action
    monkeypatch.setattr(workers,'retry_action',lambda *a: (lambda x:(x[0],0))(real_action(*a)))
    monkeypatch.setattr(privacy,'check_wire',lambda *a:None)
    item=dict(id='a'*32,rubric=e87.RUBRIC.read_text(),positions=[dict(offset=0,readout='Synthetic sample.')])
    monkeypatch.setattr(protocol,'payload',lambda *a:e87.wire([item],protocol))
    monkeypatch.setattr(protocol,'validate',lambda s,v,b,t=None:e87_classify(b,v))
    observed=[]
    def send(wire):
        observed.append(wire)
        if len(observed)==1:return 429,dict(error=dict(code=429))
        return 200,dict(provider=protocol.PROVIDER_NAME,model=protocol.MODEL,usage=dict(cost=.0001),choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(records=[dict(id=item['id'],category='silent',values=[],evidence='',first_position=0)]))))])
    client=api.Client(tmp_path/'e95_60usd','fixture',send=send)
    write(client.root/'LOW_RATE.json',dict(next_send_epoch=0,rate_limits=0))
    original=api.Client.one
    try:
        workers.patch_api(api,io,'E95')
        result=client.one('fixture',[item])
    finally:api.Client.one=original
    assert result['status']=='OK'
    assert observed==[e87.wire([item],protocol)]*2
    events=[json.loads(x) for x in client.ledger.path.read_text().splitlines()]
    assert len(events)==4 and events[1]['charge_basis']=='BOOKED_RESERVED_UPPER_BOUND'
    assert events[1]['provider_actual_cost_known'] is False
    assert events[0]['usd']==events[1]['usd']
    assert events[0]['id']!=events[2]['id']
    assert result['value'][0]['code']['first_position'] is None
