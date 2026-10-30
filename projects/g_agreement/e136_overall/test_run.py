import hashlib,json
import pytest
from .run import sealed,pointer,PINS,preflight

def fixture(tmp_path):
 p=tmp_path/'x.json';p.write_text(json.dumps([{'code':'UNPARSEABLE'}]))
 s=tmp_path/'seal.json';s.write_text(json.dumps({'files':{'x.json':hashlib.sha256(p.read_bytes()).hexdigest()}}))
 return {'seal':str(s),'sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'member':'x.json','keys':[0,'code']}
def test_pointer_preserves_missing(tmp_path):assert pointer(fixture(tmp_path))=='UNPARSEABLE'
def test_unsealed_member_rejected(tmp_path):
 r=fixture(tmp_path);r['member']='other.json'
 with pytest.raises(ValueError):pointer(r)
def test_changed_seal_rejected(tmp_path):
 r=fixture(tmp_path);r['sha256']='0'*64
 with pytest.raises(ValueError):pointer(r)
def test_old_bank_rejected_before_read():
 s={'primary_scope':'test_present','denominator_authority':'synthetic'}
 s.update({k:{'path':'not-opened','sha256':v} for k,v in PINS.items()});s['judge']['sha256']='old'
 with pytest.raises(ValueError,match='eligible component'):preflight(s)
def test_no_default_denominator():
 with pytest.raises(ValueError,match='denominator'):preflight({})
