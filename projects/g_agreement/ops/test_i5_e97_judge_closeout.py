import pytest
from projects.g_agreement.ops.i5_e97_judge_closeout import terminal_gate,diagnostic_kind

def sealed():return dict(bank='E97',primary_records=6668,old_rubric_records=1667,route_verified=True,redaction_audit_complete=True,transport217c2_finalized=True,transport217c2_authority='3f9842e1af11940fc9fdc4ff6507773c195f74f6',redacted_opaque_ids=[str(i)for i in range(227)])
def error(cost=0):return dict(http_status=200,response=dict(provider='Google',model='google/gemini-3.1-flash-lite',usage=dict(cost=cost),choices=[dict(finish_reason='error',error=dict(code=429),message=dict(content='SYNTHETIC partial'))]))
def test_only_complete_finalized_grid():
 terminal_gate(sealed())
 for key,val in [('transport217c2_finalized',False),('primary_records',100),('old_rubric_records',1),('route_verified',False)]:
  x=sealed();x[key]=val
  with pytest.raises(ValueError):terminal_gate(x)
def test_redaction_inventory_unique():
 x=sealed();x['redacted_opaque_ids']=['same']*227
 with pytest.raises(ValueError):terminal_gate(x)
def test_zero_partial_is_diagnostic_only():assert diagnostic_kind(error()).startswith('CLARIFICATION2')
def test_charged_unknown_provider_not_relaxed():
 with pytest.raises(ValueError):diagnostic_kind(error(.01))
 x=error();x['response']['provider']='Unknown'
 with pytest.raises(ValueError):diagnostic_kind(x)
def test_original_transport429_and_id_case():
 assert diagnostic_kind(dict(http_status=429,response=dict(error=dict(code=429))))=='ORIGINAL_HTTP429_NO_GENERATION'
 with pytest.raises(ValueError):diagnostic_kind(dict(http_status=429,response=dict(id='generation',choices=[])))

def test_saved_filename_matches_original_ledger_identity():
 from projects.g_agreement.ops.i5_e97_judge_closeout import request_id
 assert request_id("/ledger/batch/opaque.response.json")=="opaque"
 with pytest.raises(ValueError):request_id("opaque.json")
