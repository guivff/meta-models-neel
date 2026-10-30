import json
from pathlib import Path
import pytest
from . import run_once as r

def test_exclusive_claim(tmp_path):
 p=tmp_path/'ONCE.json';r.claim(p,{'phase':'T7'})
 before=p.read_bytes()
 with pytest.raises(FileExistsError):r.claim(p,{})
 assert p.read_bytes()==before

def test_normalization_and_hash_barriers_before_claim(tmp_path,monkeypatch):
 monkeypatch.setattr(r,'committed',lambda *a:None)
 p=tmp_path/'plan.json';p.write_text(json.dumps(dict(experiment='E134',normalization_status='PENDING')))
 with pytest.raises(ValueError,match='normalization'):r.load(p)
 p.write_text(json.dumps(dict(experiment='E134',normalization_status='AUTHORIZED_FROZEN',pins=[dict(path=str(p),sha256='wrong')])))
 with pytest.raises(ValueError,match='pin'):r.load(p)

def test_t7_cannot_load_training_types(tmp_path,monkeypatch):
 plan=dict(phase='T7',output=str(tmp_path/'out'),guard=str(tmp_path/'guard'))
 monkeypatch.setattr(r,'load',lambda p:(plan,{'T1':[]}))
 with pytest.raises(ValueError,match='T7 only'):r.run('unused')
 assert not (tmp_path/'guard').exists()


def test_t7_selection_checked_before_rows_open(tmp_path,monkeypatch):
 monkeypatch.setattr(r,'committed',lambda *a:None)
 sp=tmp_path/'selection';sp.write_text('{}')
 p=tmp_path/'plan.json';p.write_text(json.dumps(dict(experiment='E134',phase='T7',normalization_status='AUTHORIZED_FROZEN',pins=[],selection=dict(path=str(sp),commit='original',sha256='wrong'),rows=dict(path='MUST_NOT_OPEN'))))
 with pytest.raises(ValueError,match='selection pin'):r.load(p)


def test_missing_truth_rejected_before_claim(tmp_path,monkeypatch):
 monkeypatch.setattr(r,'committed',lambda *a:None)
 data=tmp_path/'rows.json';data.write_text(json.dumps({'T2':[dict(id='x',truth=None,readings={'44':'A'},source_refs={'original':'source'},truth_ref={'status':'PENDING'})]}))
 plan=tmp_path/'plan.json';plan.write_text(json.dumps(dict(experiment='E134',phase='T1_T6',normalization_status='AUTHORIZED_FROZEN',pins=[],rows=dict(path=str(data),sha256=r.sha(data)),guard=str(tmp_path/'guard'))))
 with pytest.raises(ValueError,match='truth must be bound before claim'):r.load(plan)
 assert not (tmp_path/'guard').exists()
