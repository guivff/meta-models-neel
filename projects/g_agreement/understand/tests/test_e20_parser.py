import pytest
from projects.g_agreement.understand.e20_parser import positive,positive_bullets
@pytest.mark.parametrize('row,text,expected',[
 ('prose_paren','hello) then (',True),('prose_paren','(hello)',False),('prose_paren','hello',False),
 ('python_string','- word" rest "',True),('python_string','- a "quoted" word',False),('python_string','- text "',True),
 ('prose_sentiment_delayed','Wonderful!',True),('prose_sentiment_delayed','terrible',False),('prose_sentiment_delayed','wonderfully',False),
 ('fact_once','code 1234',True),('fact_once','code 5678',False),('fact_once','12345',False),('fact_once','01234',False)])
def test_events(row,text,expected):assert positive(row,text)==expected
def test_fixed_A_not_matching_truth():assert positive_bullets('fact_once',['1234','5678','1234 and 5678','neither'])==2

def test_collector_rejects_non_kernel_environment_before_model_load(tmp_path,monkeypatch):
 import json,hashlib,sys
 from types import SimpleNamespace
 from projects.g_agreement.understand.e20_parser_dev import run
 plan=tmp_path/'plan.json';plan.write_text(json.dumps({'item_commit':'frozen'}))
 q={'issuer':'integrator','experiment':'E20_PARSER_DEV','pod_id':'testpod','plan_sha256':hashlib.sha256(plan.read_bytes()).hexdigest(),'item_commit':'frozen','external_hardstop_verified':True,'items_published':True}
 assignment=tmp_path/'assignment.json';assignment.write_text(json.dumps(q));monkeypatch.setenv('RUNPOD_POD_ID','testpod');monkeypatch.setattr(sys,'prefix','/weights/venv')
 with pytest.raises(ValueError,match='/weights/venv-kernels'):run(SimpleNamespace(assignment=assignment,plan=plan))
