from types import SimpleNamespace
from pathlib import Path
import pytest
import hashlib
from projects.g_agreement.e79_extension import hardware as H

class Original:
    def __init__(self,*args):self.args=args
    def load_oracle(self):self.loaded='H200'
    def native_one(self,*args):return 'frozen_native'

def make(tmp_path,gpu='H200',inputs=Path('refs')):
    assignment=dict(gpu_type=gpu,analysis_unit_gpu_types={'E79_extension':gpu})
    if gpu=='B200'and inputs is not None:
        inputs=tmp_path/'refs';inputs.mkdir(exist_ok=True)
        for name in ['SMOKE_oracle.json','SMOKE_oracle.npy']:(inputs/name).write_bytes(b'fixture')
        assignment['hardware_reference_files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in inputs.iterdir()}
    return H.backend(SimpleNamespace(Backend=Original),Path('.'),Path('assets'),assignment,inputs,tmp_path,lambda *a:None)

def test_same_native_method_and_h200_loader(tmp_path,monkeypatch):
    monkeypatch.setattr(H,'check_device',lambda gpu:dict(gpu_type=gpu));b=make(tmp_path);b.load_oracle()
    assert b.loaded=='H200'and type(b).native_one is Original.native_one
    assert b.args[-1]=={'gpu_type':'H200'}

def test_b200_load_then_smoke_and_failure_stops(tmp_path,monkeypatch):
    events=[];monkeypatch.setattr(H,'check_device',lambda gpu:{})
    monkeypatch.setattr(H,'load_b200',lambda b:events.append('load'))
    monkeypatch.setattr(H,'smoke',lambda *a:events.append('smoke'))
    b=make(tmp_path,'B200');b.load_oracle();assert events==['load','smoke']and type(b).native_one is Original.native_one
    def fail(b):raise RuntimeError('load failed')
    monkeypatch.setattr(H,'load_b200',fail);events.clear()
    with pytest.raises(RuntimeError,match='load failed'):b.load_oracle()
    assert events==[]

def test_assignment_scope_and_reference_required(tmp_path):
    with pytest.raises(ValueError):make(tmp_path,'A100')
    with pytest.raises(ValueError):make(tmp_path,'B200',None)
    with pytest.raises(ValueError):H.backend(SimpleNamespace(Backend=Original),Path('.'),Path('assets'),dict(gpu_type='H200',analysis_unit_gpu_types={'real':'H200','control':'B200'}),None,tmp_path,lambda *a:None)


def test_changed_smoke_fixture_rejected_before_load(tmp_path):
    inputs=tmp_path/'bad';inputs.mkdir()
    for name in ['SMOKE_oracle.json','SMOKE_oracle.npy']:(inputs/name).write_bytes(b'changed')
    a=dict(gpu_type='B200',analysis_unit_gpu_types={'E79_extension':'B200'},hardware_reference_files={n:'0'*64 for n in ['SMOKE_oracle.json','SMOKE_oracle.npy']})
    with pytest.raises(ValueError,match='fixture changed'):
        H.backend(SimpleNamespace(Backend=Original),Path('.'),Path('assets'),a,inputs,tmp_path,lambda *a:None)
