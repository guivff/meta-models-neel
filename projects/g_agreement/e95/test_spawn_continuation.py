import hashlib,json
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
import pytest

from projects.g_agreement.e95.judge_dispatch import send_items
from projects.g_agreement.e95.judging_stages import continuation
from projects.g_agreement.understand.blind_judge import e87
from projects.g_agreement.readerbench.io import read,write,sha


def test_unknown_group_is_missing_and_never_calls_any_client(tmp_path):
    item=dict(id='a'*32,rubric='frozen',positions=[])
    class Client:
        def one(self,*args):raise AssertionError('an unknown request was replayed')
    state=dict(io=None,client=Client(),protocol=None,spec=dict(ledger_root=str(tmp_path)),
               allowed={item['id']:item},stage_prefix='unchanged',preserved_missing={item['id']:'reserved'})
    rows=send_items(state,[item],0)
    assert rows[0]['code']is None and rows[0]['status']=='UNPARSEABLE'
    assert rows[0]['terminal_reason']=='UNKNOWN_REQUEST_NO_REPLAY'


def test_continuation_preserves_original_guard_requests_and_reservations(tmp_path):
    ledger=tmp_path/'e95_60usd';ledger.mkdir();old=tmp_path/'stopped';old.mkdir()
    protocol=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global')
    item=dict(id='a'*32,rubric=e87.RUBRIC.read_text(),positions=[dict(offset=0,readout='Synthetic sample.')])
    packet='b'*64;wire=e87.wire([item],protocol)
    canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'))
    rid=hashlib.sha256(('E95_'+packet[:16]+':0:'+canonical(wire)).encode()).hexdigest()
    folder=ledger/('E95_'+packet[:16]+'_attempt0');folder.mkdir()
    request=folder/(rid+'.request.json');write(request,dict(wire=wire,upper_usd='1'))
    write(old/'START.json',dict(synthetic=True))
    write(old/'JUDGMENT_SEAL.json',dict(status='BLOCKED_PARTIAL_NO_ANALYSIS',files={'START.json':sha(old/'START.json')}))
    guard=ledger/'STAGE1_ONCE.json';write(guard,dict(packet_seal_sha256=packet,out=str(old)))
    original=guard.read_bytes();request_bytes=request.read_bytes()
    api=SimpleNamespace(Ledger=lambda p:SimpleNamespace(totals=lambda:({rid:Decimal(1)},set())))
    spec=dict(ledger_root=str(ledger),judging_stage=1,packet_seal_sha256=packet,out=str(tmp_path/'new'),
              preserved_missing={item['id']:rid},continuation=dict(original_once_sha256=sha(guard),
              previous_partial_seal=str(old/'JUDGMENT_SEAL.json'),previous_partial_seal_sha256=sha(old/'JUDGMENT_SEAL.json'),
              preserved_missing={item['id']:rid},request_sha256={rid:sha(request)}))
    path=continuation(spec,[item],api,protocol,SimpleNamespace(canonical=canonical))
    assert guard.read_bytes()==original and request.read_bytes()==request_bytes
    assert read(path)['resend_unknown']is False and read(path)['reset_guard']is False
    with pytest.raises(FileExistsError):continuation(spec,[item],api,protocol,SimpleNamespace(canonical=canonical))
