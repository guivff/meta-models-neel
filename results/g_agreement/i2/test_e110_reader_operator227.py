import copy,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from e110_reader_contract227 import verify_shape
class ContractTests(unittest.TestCase):
 def good(self):return dict(experiment='E110_READERS',gpu_type='H200',cap_seconds=5400,prior_probe_gpu_seconds=0,gpu_forecast_upper_usd=9.94,selected_count=120,fresh_extract_cpu_import_pass=True,adapter_pre_output_verified=True,C_channel_pre_output_verified=True,minimum_native_staging_need_seconds=1000,inventory_commit='a'*40,selection_guard_original=True,all_selected_items_retained=True)
 def test_admit_registered_shape(self):self.assertTrue(verify_shape(self.good()))
 def reject(self,k,v):
  d=self.good();d[k]=v
  with self.assertRaises((AssertionError,TypeError)):verify_shape(d)
 def test_h100_refused(self):self.reject('gpu_type','H100')
 def test_cap_raise_refused(self):self.reject('cap_seconds',5401)
 def test_native_minimum_no_fit(self):self.reject('minimum_native_staging_need_seconds',5401)
 def test_uncommitted_inventory_refused(self):self.reject('inventory_commit','uncommitted')
 def test_no_gate_floor_rescue(self):self.reject('selected_count',59)
 def test_no_sampling_flag(self):self.reject('all_selected_items_retained',False)
 def test_adapter_required(self):self.reject('adapter_pre_output_verified',False)
 def test_C_required(self):self.reject('C_channel_pre_output_verified',False)
 def test_no_clock_reuse(self):self.reject('prior_probe_gpu_seconds',1)
if __name__=='__main__':unittest.main()

class SealSafetyTests(unittest.TestCase):
 def setUp(self):
  import tempfile,json
  from e110_reader_contract227 import sha
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  (self.root/'member.json').write_text('{"original":true}')
  self.seal=self.root/'SEAL.json';self.seal.write_text(json.dumps({'files':{'member.json':sha(self.root/'member.json')}}))
 def test_original_members_verified(self):
  from e110_reader_contract227 import sha,verify_seal
  self.assertEqual(len(verify_seal(self.seal,sha(self.seal))['files']),1)
 def test_changed_raw_member_rejected(self):
  from e110_reader_contract227 import sha,verify_seal
  (self.root/'member.json').write_text('{"original":false}')
  with self.assertRaises(AssertionError):verify_seal(self.seal,sha(self.seal))
 def test_changed_seal_rejected(self):
  from e110_reader_contract227 import verify_seal
  with self.assertRaises(AssertionError):verify_seal(self.seal,'0'*64)
 def test_traversal_member_rejected(self):
  import json
  from e110_reader_contract227 import sha,verify_seal
  self.seal.write_text(json.dumps({'files':{'../outside.json':'0'*64}}))
  with self.assertRaises(AssertionError):verify_seal(self.seal,sha(self.seal))
