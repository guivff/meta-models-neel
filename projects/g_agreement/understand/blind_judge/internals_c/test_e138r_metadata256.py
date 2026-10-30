import tempfile,unittest
from pathlib import Path
from .e138r_metadata256 import companion,INPUT
from projects.g_agreement.readerbench.io import read,write,sha
class Tests(unittest.TestCase):
 def fixture(self,d):
  p=Path(d);write(p/'JUDGMENTS.json',[dict(id=str(i),kind='E138R',code=None,status='UNPARSEABLE')for i in range(168)]);s=p/'JUDGMENT_SEAL.json';write(s,dict(experiment='E138R',status='COMPLETE',input_sha256=INPUT,files={'JUDGMENTS.json':sha(p/'JUDGMENTS.json')}));return s
 def test_alias_without_any_byte_change(self):
  with tempfile.TemporaryDirectory()as d:
   s=self.fixture(d);before={p.name:p.read_bytes()for p in Path(d).iterdir()};p=companion(s,Path(d)/'COMPAT.json');self.assertEqual(read(p)['input_seal_sha256'],INPUT);self.assertEqual(read(p)['files'],read(s)['files']);self.assertTrue(all((Path(d)/n).read_bytes()==b for n,b in before.items()))
 def test_wrong_input_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   s=self.fixture(d);a=read(s);a['input_sha256']='wrong';write(s,a)
   with self.assertRaises(Exception):companion(s,Path(d)/'COMPAT.json')
 def test_member_tamper_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   s=self.fixture(d);write(Path(d)/'JUDGMENTS.json',[])
   with self.assertRaises(Exception):companion(s,Path(d)/'COMPAT.json')
