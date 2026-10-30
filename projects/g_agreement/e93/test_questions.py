import hashlib,json,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_frozen_coverage_and_one_line(self):
  seal=json.loads((HERE/'QUESTIONS_SEAL.json').read_text());self.assertEqual(hashlib.sha256((HERE/'questions.json').read_bytes()).hexdigest(),seal['questions_sha256'])
  q=json.loads((HERE/'questions.json').read_text());self.assertEqual({k:len(v) for k,v in q.items()},seal['question_counts'])
  self.assertEqual(set(q),{'E57','E59','E62','E82'})
  for bank,rows in q.items():
   for row,text in rows.items():self.assertTrue(text.strip());self.assertNotIn('\n',text);self.assertNotIn('{',text)
  self.assertEqual(len(set(q['E82'].values())),1)
if __name__=='__main__':unittest.main()
