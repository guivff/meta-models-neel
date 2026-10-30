import json
from types import SimpleNamespace
from decimal import Decimal
import pytest
from projects.g_agreement.e96 import separate_dispatch217 as d

def test_length_is_terminal_missing_no_singleton_retry():
 calls=[]
 def send(batch,attempt):
  calls.append((len(batch),attempt));return [dict(id=x['id'],status='UNPARSEABLE',code=None,terminal_reason='charged_length') for x in batch]
 items=[{'id':str(i)} for i in range(4)];rows=d.judge_terminal(items,send);flat,audit=d.adapt_terminal(rows,items)
 assert calls==[(4,0)] and all(x['category']=='UNPARSEABLE' for x in flat)
 assert all(x['attempts']==0 and not x['retried_after_length'] for x in audit)

def test_validation_failure_retains_original_two_retry_limit():
 calls=[]
 def send(batch,attempt):calls.append(attempt);return [dict(id=x['id'],status='UNPARSEABLE',code=None) for x in batch]
 rows=d.judge_terminal([{'id':'a'}],send);assert calls==[0,1,2] and rows[0]['attempts']==2

def test402_latches_all_and_keeps_private_payload_out(tmp_path,monkeypatch):
 p=tmp_path/'pause';monkeypatch.setattr(d,'PAUSE',p)
 with pytest.raises(RuntimeError,match='all banks pause'):d.audit({'http_status':402,'response':{'private_account':'do not publish'}},None)
 assert p.exists() and 'private_account' not in p.read_text()

def test_length_rejects_unknown_charge_route_and_error():
 protocol=SimpleNamespace(PROVIDER_NAME='Google',MODEL='model')
 s={'http_status':200,'response':{'model':'model','provider':'Google','usage':{'cost':.2},'choices':[{'finish_reason':'length'}]}}
 assert d.audit(s,protocol)['terminal_length'];s['response']['provider']='other'
 with pytest.raises(ValueError):d.audit(s,protocol)

def test_budget_cumulative_bank_and_updated_global(tmp_path):
 p=tmp_path/'a';base={'issuer':'I-4','bank':'E96','verified':True,'packet_seal_sha256':'p','allocation_usd':50,'prior_E96_actual_usd':'10.31937525','global_judging_committed_including_e96_usd':900,'global_evidence':['fresh'],'allocation_authority':'217'}
 p.write_text(json.dumps(base));assert d.budget(p,'p')==50
 for delta in [{'allocation_usd':110},{'global_judging_committed_including_e96_usd':1001},{'verified':False}]:
  p.write_text(json.dumps(dict(base,**delta)))
  with pytest.raises(ValueError):d.budget(p,'p')

def test_runtime_scientific_code_unchanged_except_audited_transport_anchors():
 f,original,patched=d.runtime();assert "global_pause.exists()" in patched
 for text in ['current=amended().decode()','max_tokens','redact(items,','identity(batch,attempt']:
  assert original.count(text)==patched.count(text)
 assert 'separate_slot1/ledger' in patched and callable(f)

def test_pinned_actual_shared_pacing_loads_without_unrelated_science():
 p=d.shared_pacer();assert p.f.CACHE==d.SHARED_QUEUE and callable(p.patch_api) and callable(p.claim_slot)
