import unittest,json,hashlib,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
class FrozenBankTests(unittest.TestCase):
 def setUp(self):
  self.records=load(HERE/'cache/bank_2026-10-27_v2/INPUTS.json');self.labels={x['id']:x for x in load(HERE/'cache/bank_2026-10-27_v2/LABELS.PRIVATE.json')}
 def test_seal(self):
  for p,h in load(HERE/'BANK_SEAL.json')['files'].items():self.assertEqual(hashlib.sha256((HERE/p).read_bytes()).hexdigest(),h)
 def test_pairs_and_targets(self):
  pairs={}
  for x in self.records:pairs.setdefault((x['bank'],x['source_item_id']),[]).append(x)
  self.assertEqual(len(pairs),1092)
  for pair in pairs.values():
   self.assertEqual(len(pair),2);a,b=pair
   self.assertEqual(a['text'][:-len(a['suffix'])],b['text'][:-len(b['suffix'])])
   self.assertEqual(self.labels[a['id']]['alpha_target']+self.labels[b['id']]['alpha_target'],1)
 def test_page_bin(self):
  for x in self.records:
   if x['feature']!='page_range_digit':continue
   source=x['text'][:-len(x['suffix'])];digit=int(re.search(r'Current citation: pp\. (\d)',source)[1])
   self.assertEqual(int(digit in (1,2,3,4)),self.labels[x['id']]['label'])
   self.assertIn('1, 2, 3, or 4' if x['arm']=='normal' else '6, 7, 8, or 9',x['suffix'])
 def test_balanced_no_label_in_gpu_record(self):
  for r in load(HERE/'SELECTION.json')['selected'].values():
   for row in r:
    for arm in ('normal','swapped'):
     xs=[x for x in self.records if x['feature']==row and x['arm']==arm]
     self.assertEqual(len(xs),84);self.assertEqual(sum(self.labels[x['id']]['alpha_target'] for x in xs),42)
     self.assertEqual(len({x['suffix'] for x in xs}),1)
  self.assertTrue(all('label' not in x and 'value' not in x for x in self.records))
if __name__=='__main__':unittest.main()
