from decimal import Decimal
from pathlib import Path
import pytest
from . import e79b_judging as e
from . import transport217c2_e79b as w
from . import transport217c2 as original
from .operational217 import judge,truncated
from projects.g_agreement.readerbench.io import write


def test_separate_lifetime_namespace_and_original_transport():
    assert e.CAP==Decimal('3') and e.CACHE.name=='E79_ARM_B'
    assert w.MAX_RETRIES==2 and w.REASON==original.REASON and w.AUTHORITY==original.AUTHORITY
    assert 'E79_ARM_B'in Path(w.__file__).read_text()


def test_evidence_valid_original_preserved_redacted_placeholder_missing():
    raw=[dict(id='one',readout='plain source text'),dict(id='two',readout='private source location'),dict(id='three',readout='quiet')]
    codes=[dict(id='one',category='states_value',values=['A'],evidence='source text'),dict(id='two',category='exhibits',values=[],evidence='[REDACTED_PATH]'),dict(id='three',category='UNPARSEABLE',values=[],evidence='')]
    flat,audit=e.source_safe(codes,raw)
    assert flat[0]==codes[0] and flat[1]['category']=='UNPARSEABLE' and flat[2]==codes[2]
    assert audit==[dict(id='two',reason='JUDGE_COPY_EVIDENCE_NOT_VALID_ON_ORIGINAL_SOURCE')]
    assert codes[1]['evidence']=='[REDACTED_PATH]'  # immutable original judge code


def test_terminal_length_not_retried_and_schema_invalid_bounded():
    calls=[];items=[dict(id='x',readout='')]
    def send(batch,attempt):calls.append(attempt);return truncated(batch)
    assert judge(items,send)[0]['terminal_reason']=='CHARGED_LENGTH' and calls==[0]
    calls=[]
    def invalid(batch,attempt):calls.append(attempt);return [dict(id='x',status='INVALID',code=None)]
    assert judge(items,invalid)[0]['status']=='UNPARSEABLE'and calls==[0,1,2]


def test_known_failure_wrapper_same_eligibility_and_nonzero_stop():
    from types import SimpleNamespace
    p=SimpleNamespace(MODEL='m',PROVIDER_NAME='p')
    saved=dict(http_status=200,response=dict(model='m',provider='p',usage=dict(cost=0),choices=[dict(finish_reason='error')]))
    assert w.eligible(saved,p)==original.eligible(saved,p) is True
    saved['response']['usage']['cost']=.1
    assert not w.eligible(saved,p)


def test_prepare_static_only_no_ledger_or_call(tmp_path,monkeypatch):
    import types
    cfg=dict(blind=str(tmp_path/'blind'),private=str(tmp_path/'join'),output_sha256='out')
    (tmp_path/'blind').mkdir();(tmp_path/'blind/BLIND_SEAL.json').write_text('source');(tmp_path/'join').write_text('private')
    (tmp_path/'CAP_BINDING.json').write_text('cap')
    (tmp_path/'SPEC.json').write_text('spec')
    monkeypatch.setattr(e,'OWNER',tmp_path);monkeypatch.setattr(e,'CACHE',tmp_path/'cache');monkeypatch.setattr(e,'source_gate',lambda:None)
    monkeypatch.setattr(e,'packet',lambda path:(cfg,[dict(id=str(i),readout='text',rubric='r')for i in range(672)],'rubric'))
    api=types.SimpleNamespace(upper=lambda wire:Decimal('.001'));privacy=types.SimpleNamespace(check_wire=lambda *a:None)
    monkeypatch.setattr(e.funded,'route_api',lambda:(None,(api,privacy,object(),None)))
    monkeypatch.setattr(e,'channel_payload',lambda *args:dict(messages=[dict(content='r'),dict(content='[]')]))
    monkeypatch.setattr(e,'check_decoded',lambda *args:None)
    monkeypatch.setattr(e,'HERE',tmp_path/'source');e.HERE.mkdir();(e.HERE/'SOURCE_SEAL.json').write_text('source')
    result=e.prepare(tmp_path/'SPEC.json')
    assert result['records']==672 and result['initial_requests']==168 and result['paid_calls']==0
    assert not (e.CACHE/'ledger').exists()
