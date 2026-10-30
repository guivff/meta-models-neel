import datetime,json,time
import pytest
from projects.g_agreement.e102 import launch_gate as l

def admission(root):
 d={'as_of_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'posted_shared_commit':'commit','gate_only':True,'training_admitted':False,'core_priority_checked':True,'projected_all_track_upper_usd':849.52,'gpu_type':'B200','existing_active_names':['core'],'quote_usd_hour':7.99,'core_reserved_hourly_headroom_usd':21.16,'provider_hourly_limit_usd':80}
 (root/'POSTED_ADMISSION.json').write_text(json.dumps(d));(root/'STAGING_PLAN.json').write_text(json.dumps({'files':{}}));return d

def test_duplicate_refused_before_network(monkeypatch,tmp_path):
 (tmp_path/'STATE.json').write_text('{}');monkeypatch.setattr(l,'query',lambda q:pytest.fail('network onduplicate'))
 with pytest.raises(ValueError,match='never duplicate'):l.launch(tmp_path)

def test_training_manifest_refused(monkeypatch,tmp_path):
 d=admission(tmp_path);d['training_admitted']=True;(tmp_path/'POSTED_ADMISSION.json').write_text(json.dumps(d));monkeypatch.setattr(l,'query',lambda q:pytest.fail('network ontraining'))
 with pytest.raises(ValueError,match='gate-only'):l.launch(tmp_path)

def test_capacity_reserves_CORE_headroom_no_create(monkeypatch,tmp_path):
 admission(tmp_path);calls=[]
 def query(q):
  calls.append(q);assert 'mutation' not in q
  return {'myself':{'pods':[{'id':'core','name':'core','desiredStatus':'RUNNING','costPerHr':55}]},'gpuTypes':[{'securePrice':7.99}]}
 monkeypatch.setattr(l,'query',query)
 with pytest.raises(ValueError,match='headroom'):l.launch(tmp_path)
 assert len(calls)==1 and not (tmp_path/'CREATE_REQUEST.json').exists()

def test_unreconciled_new_pod_prevents_create(monkeypatch,tmp_path):
 admission(tmp_path);monkeypatch.setattr(l,'query',lambda q:{'myself':{'pods':[{'id':'new','name':'new','desiredStatus':'RUNNING','costPerHr':5.29}]},'gpuTypes':[{'securePrice':7.99}]})
 with pytest.raises(ValueError,match='new allocation'):l.launch(tmp_path)
 assert not (tmp_path/'CREATE_REQUEST.json').exists()

def test_stale_admission_refused_before_network(monkeypatch,tmp_path):
 d=admission(tmp_path);d['as_of_utc']='2020-01-01T00:00:00+00:00';(tmp_path/'POSTED_ADMISSION.json').write_text(json.dumps(d));monkeypatch.setattr(l,'query',lambda q:pytest.fail('network onstale'))
 with pytest.raises(ValueError,match='fresh admission'):l.launch(tmp_path)

def test_create_timeout_is_ambiguous_and_never_resubmitted(monkeypatch,tmp_path):
 admission(tmp_path);calls=[]
 def query(q):
  calls.append(q)
  return {'myself':{'pods':[]},'gpuTypes':[{'securePrice':7.99}]}
 def run(*a,**k):raise l.subprocess.TimeoutExpired('CREATE',90)
 monkeypatch.setattr(l,'query',query);monkeypatch.setattr(l.subprocess,'run',run)
 with pytest.raises(RuntimeError,match='ambiguous'):l.launch(tmp_path)
 assert (tmp_path/'CREATE_REQUEST.json').exists() and len(calls)==2
 with pytest.raises(ValueError,match='never duplicate'):l.launch(tmp_path)
