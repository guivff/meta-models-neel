import json,unittest,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_templates(self):
  data=json.loads((P/'TEMPLATES.json').read_text())
  for row,values in data['rows'].items():
   self.assertEqual(len(values),2)
   for value,templates in values.items():
    self.assertEqual(len(set(templates)),5)
    n={'one':'1','three':'3','four':'4','twelve':'12'}[value]
    for s in templates:
     self.assertTrue(s.startswith('- '));self.assertNotIn('\n',s);self.assertIn(n,s)
 def test_seal(self):
  seal=json.loads((P/'TEMPLATES_SEAL.json').read_text())
  for name,digest in seal['files'].items():self.assertEqual(hashlib.sha256((P/name).read_bytes()).hexdigest(),digest)
if __name__=='__main__':unittest.main()
