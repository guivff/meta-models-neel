import unittest,tempfile,json
from pathlib import Path
from .e118b_metadata251 import corrected_metadata,frozen_metadata_preflight
from .transport import ROOT
from projects.g_agreement.readerbench.io import write,sha,read
class Tests(unittest.TestCase):
 def setUp(self):self.old=dict(experiment='E118',status='COMPLETE',phase='part_b',input_sha256='input',E118b_source_seal_sha256='source',route_verified=True,labels_cpu_only=True,redaction_audit_complete=True,redacted_records=0,files={'RESPONSES.json':'unchanged'})
 def test_only_two_metadata_fields(self):
  v=corrected_metadata(self.old,'input');self.assertEqual(self.old['phase'],'part_b');self.assertNotIn('input_seal_sha256',self.old);self.assertEqual({k:x for k,x in v.items()if k not in('phase','input_seal_sha256')},{k:x for k,x in self.old.items()if k!='phase'})
 def fixture(self,root,fixed):
  (root/'j').mkdir();(root/'c').mkdir();write(root/'j/RESPONSES.json',[]);s=corrected_metadata(self.old,'input')if fixed else dict(self.old);s['files']={'RESPONSES.json':sha(root/'j/RESPONSES.json')};write(root/'j/JUDGMENT_SEAL.json',s)
  write(root/'c/CAP_SETTLEMENT.json',dict(bank='E118',lifetime_USD=1,prior_actual_USD=.027057,unknown_USD=0,total_actual_USD=.853200125,judgment_sha256=sha(root/'j/JUDGMENT_SEAL.json')));write(root/'c/JUDGMENT_SEAL.json',dict(files={'CAP_SETTLEMENT.json':sha(root/'c/CAP_SETTLEMENT.json')}))
  a=ROOT/'projects/g_agreement/e118b_analysis/adapter.py';write(root/'source.json',dict(files={'projects/g_agreement/e118b_analysis/adapter.py':sha(a)}));return dict(judgment_seal=str(root/'j/JUDGMENT_SEAL.json'),judgment_sha256=sha(root/'j/JUDGMENT_SEAL.json'),input_sha256='input',report_source_sha256='source',report_source_seal=str(root/'source.json'),cap_seal=str(root/'c/JUDGMENT_SEAL.json'),cap_sha256=sha(root/'c/JUDGMENT_SEAL.json'))
 def test_real_frozen_assertions_accept_fixed(self):
  with tempfile.TemporaryDirectory()as t:self.assertEqual(len(frozen_metadata_preflight(self.fixture(Path(t),True))),4)
 def test_real_frozen_assertions_reject_old(self):
  with tempfile.TemporaryDirectory()as t:
   with self.assertRaises(Exception):frozen_metadata_preflight(self.fixture(Path(t),False))
 def test_real_frozen_assertions_reject_wrong_input(self):
  with tempfile.TemporaryDirectory()as t:
   s=self.fixture(Path(t),True);s['input_sha256']='wrong'
   with self.assertRaises(Exception):frozen_metadata_preflight(s)
 def test_real_frozen_assertions_reject_wrong_cap_binding(self):
  with tempfile.TemporaryDirectory()as t:
   r=Path(t);s=self.fixture(r,True);v=read(r/'c/CAP_SETTLEMENT.json');v['judgment_sha256']='old';write(r/'c/CAP_SETTLEMENT.json',v);write(r/'c/JUDGMENT_SEAL.json',dict(files={'CAP_SETTLEMENT.json':sha(r/'c/CAP_SETTLEMENT.json')}));s['cap_sha256']=sha(r/'c/JUDGMENT_SEAL.json')
   with self.assertRaises(Exception):frozen_metadata_preflight(s)
