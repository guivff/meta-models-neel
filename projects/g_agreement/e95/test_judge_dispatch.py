from decimal import Decimal
from pathlib import Path
import pytest
from types import SimpleNamespace

from projects.g_agreement.e95.judge_dispatch import calls_and_bound, seal_job
from projects.g_agreement.understand.blind_judge import e87
from projects.g_agreement.readerbench.io import write, read, verify, sha


def test_existing_grouped_wire_and_old_rubric_are_reused_exactly():
    protocol = SimpleNamespace(MODEL='google/gemini-3.1-flash-lite', PROVIDER='google-vertex/global')
    item = dict(id='a'*32, rubric=e87.RUBRIC.read_text(),
                positions=[dict(offset=-1,readout='Earlier.'),dict(offset=0,readout='Later.')])
    observed = []
    def upper(wire):
        observed.append(wire)
        return Decimal('1')
    original, bound = calls_and_bound([item], [item['id']], SimpleNamespace(upper=upper), protocol)
    assert bound == 2 and len(observed) == 2
    assert observed[0] == e87.wire([item], protocol)
    assert observed[1] == e87.wire(original, protocol, e87.ORIGINAL.read_text())
    assert original[0]['positions'] == item['positions']


def test_archive_preserves_original_response_mtime_and_recursive_hashes(tmp_path):
    import os
    ledger=tmp_path/'e95_60usd';stage=ledger/'E95_fixture_attempt0';stage.mkdir(parents=True)
    response=stage/('a'*32+'.response.json');write(response,dict(http_status=200,response={}))
    t=1700000000123456789;os.utime(response,ns=(t,t))
    previous=ledger/'E95_previous_attempt0';previous.mkdir()
    p=previous/'old.response.json';write(p,dict(previous=True));os.utime(p,ns=(t-1000,t-1000))
    out=tmp_path/'out';out.mkdir()
    seal_job(out,ledger,dict(experiment='E95',status='FIXTURE'),'E95_fixture')
    seal=verify(out/'JUDGMENT_SEAL.json',sha(out/'JUDGMENT_SEAL.json'))
    evidence=seal['first_output_evidence']
    assert evidence['mtime_ns'] == t and (out/evidence['member']).stat().st_mtime_ns == t
    assert evidence['sha256'] == sha(response)
    assert evidence['member'] in seal['files']
    assert not any('previous' in p for p in seal['files'])


@pytest.mark.parametrize('mode',['normal','length','402'])
def test_offline_transport_reuses_ledger_retries_and_exports_first_output(monkeypatch,tmp_path,mode):
    import json
    from pathlib import Path
    from projects.g_agreement.e95 import judge_dispatch as dispatch
    from projects.g_agreement.understand.blind_judge.run import ROOT, route_modules
    route_path=ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'
    route=read(route_path);api,privacy,protocol,io=route_modules(route)
    item=dict(id='c'*32,rubric=e87.RUBRIC.read_text(),positions=[dict(offset=0,readout='A sample.')])
    _,bound=calls_and_bound([item],[item['id']],api,protocol)
    budget=tmp_path/'BUDGET.json'
    write(budget,dict(issuer='integrator',verified=True,reservation_included=True,
                     E95_allocation_usd=60,global_judging_committed_including_reservation_usd=60,issued_epoch=dispatch.time.time(),higher_priority_banks_cleared=True))
    source=tmp_path/'SOURCE.json'
    names=dispatch.ADAPTER_FILES
    write(source,dict(experiment='E95',kind='judge source binding',files={p:sha(ROOT/p) for p in names}))
    monkeypatch.setattr(dispatch.funded_queue,'CACHE',tmp_path/'shared')
    monkeypatch.setattr(dispatch,'patch_api',lambda *args:None) # no shared pacing state in fixture
    actual_check=dispatch.subprocess.check_output
    def git_fixture(args,**kw):
        if args[:2]==['git','show']:return (ROOT/args[2].removeprefix('HEAD:')).read_bytes()
        return actual_check(args,**kw)
    monkeypatch.setattr(dispatch.subprocess,'check_output',git_fixture)
    observed=[]
    def fake_send(wire):
        observed.append(wire)
        if mode=='402':return 402,dict(error=dict(code=402))
        codes={} if len(observed)==1 else dict(records=[dict(id=item['id'],category='silent',
                          values=[],evidence='',first_position=0)])
        return 200,dict(model=protocol.MODEL,provider=protocol.PROVIDER_NAME,usage=dict(cost=.0001),
            choices=[dict(finish_reason='length'if mode=='length'else'stop',message=dict(content=json.dumps(codes)))])
    real_client=api.Client
    class FakeClient(real_client):
        def __init__(self,root,key):super().__init__(root,key,send=fake_send)
    monkeypatch.setattr(api,'Client',FakeClient)
    monkeypatch.setattr(privacy,'check_route',lambda key:dict(offline_fixture=True))
    def forbid_network(*args,**kwargs):
        raise AssertionError('network forbidden in offline transport test')
    monkeypatch.setattr(api.requests,'post',forbid_network)
    monkeypatch.setattr(dispatch,'admission',lambda spec:([item],[item['id']]))
    spec=dict(source_seal=str(source),source_seal_sha256=sha(source),
              route=str(route_path),route_sha256=sha(route_path),
              budget_receipt=str(budget),first_pass_worst_case_usd=str(bound),
              ledger_root=str(tmp_path/'e95_60usd'),out=str(tmp_path/'result'),
              packet_seal_sha256='d'*64,index_sha256='e'*64)
    if mode=='402':
        with pytest.raises(RuntimeError,match='HTTP402'):dispatch.execute(spec,key='offline-fixture',preflight=False)
        assert read(tmp_path/'shared/PAUSED_402.json')['http_status']==402
        assert len(observed)==1
        return
    result=dispatch.execute(spec,key='offline-fixture',preflight=False)
    if mode=='length':
        assert result['kept']==0 and result['unparseable']==1 and len(observed)==2
        row=read(tmp_path/'result/JUDGMENTS.json')[0]
        assert row['terminal_reason']=='CHARGED_LENGTH'and row['attempts']==0
        return
    assert result['kept']==1 and result['original_n']==1 and len(observed)==3
    assert observed[0]==observed[1]  # Unchanged wire, singleton validation retry only.
    seal=verify(tmp_path/'result/JUDGMENT_SEAL.json',sha(tmp_path/'result/JUDGMENT_SEAL.json'))
    assert seal['first_output_utc']!='unknown'
    assert seal['first_output_evidence']['member'] in seal['files']
    assert read(tmp_path/'result/JUDGMENTS.json')[0]['attempts']==1


def test_uncommitted_source_fails_before_any_packet_open(monkeypatch,tmp_path):
    from projects.g_agreement.e95 import judge_dispatch as dispatch
    root=Path(dispatch.__file__).resolve().parents[3]
    source=tmp_path/'SOURCE.json'
    write(source,dict(experiment='E95',kind='judge source binding',files={p:sha(root/p)for p in dispatch.ADAPTER_FILES}))
    monkeypatch.setattr(dispatch.subprocess,'check_output',lambda *a,**kw:b'uncommitted')
    monkeypatch.setattr(dispatch,'admission',lambda *args:pytest.fail('packet opened before source gate'))
    with pytest.raises(ValueError,match='committed'):
        dispatch.execute(dict(source_seal=str(source),source_seal_sha256=sha(source)))
