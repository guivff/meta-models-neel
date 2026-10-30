import importlib.util,json,pathlib,sys,time
import pytest
from projects.g_agreement.e102 import gate_custody

@pytest.fixture
def module(monkeypatch):
 monkeypatch.setitem(sys.modules,'gate_custody',gate_custody)
 path=pathlib.Path(__file__).with_name('gate_stage.py');spec=importlib.util.spec_from_file_location('e102_gate_stage_fixture',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 monkeypatch.setattr(m,'owned',lambda *a:pytest.fail('network before staging validation'))
 monkeypatch.setattr(m,'ssh',lambda *a,**kw:pytest.fail('SSH before staging validation'))
 return m

def base(tmp_path):
 (tmp_path/'STATE.json').write_text(json.dumps({'created_epoch':time.time(),'pod_id':'owned'}))
 return {'experiment':'E102_GATE','training_admitted':False,'files':{}}

def test_stage_refuses_production_training_manifest(module,tmp_path):
 d=base(tmp_path);d['training_admitted']=True;(tmp_path/'STAGING_PLAN.json').write_text(json.dumps(d))
 with pytest.raises(ValueError,match='gate-only'):module.stage(tmp_path)
 assert not (tmp_path/'STAGE_CLAIM.json').exists()

def test_stage_refuses_changed_payload_before_network(module,tmp_path):
 d=base(tmp_path);d['files']={'payload':'wronghash'};(tmp_path/'payload').write_text('actual');(tmp_path/'STAGING_PLAN.json').write_text(json.dumps(d))
 with pytest.raises(ValueError,match='payload changed'):module.stage(tmp_path)
 assert not (tmp_path/'STAGE_CLAIM.json').exists()

def test_stage_claim_cannot_repeat(module,tmp_path):
 d=base(tmp_path);(tmp_path/'STAGING_PLAN.json').write_text(json.dumps(d));(tmp_path/'STAGE_CLAIM.json').write_text('{}')
 with pytest.raises(ValueError,match='never automatically repeated'):module.stage(tmp_path)
