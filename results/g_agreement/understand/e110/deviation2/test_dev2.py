import unittest
from build_dev2 import frequencies,allocation,render
class Tests(unittest.TestCase):
 def test_frequency_counts_any_position_once_per_record(self):
  rows=[{'e1.wikidata_qid':'Q1','e2.wikidata_qid':'Q1','e3.wikidata_qid':'Q2'},{'e1.wikidata_qid':'Q3','e2.wikidata_qid':'Q2','e3.wikidata_qid':'Q4'}]
  f=frequencies(rows);self.assertEqual(f['Q1'],1);self.assertEqual(f['Q2'],2)
 def test_strict_less_than10(self):
  r={'e1.wikidata_qid':'Q1','e2.wikidata_qid':'Q2','e3.wikidata_qid':'Q3'}
  self.assertLess(frequencies([r]*9)['Q2'],10);self.assertFalse(frequencies([r]*10)['Q2']<10)
 def test_capped_stratification(self):
  self.assertEqual(allocation({'a':1,'b':100,'c':100},10),{'a':1,'b':5,'c':4})
  self.assertEqual(sum(allocation({str(i):100 for i in range(52)},3000).values()),3000)
 def test_template_render_does_not_insert_bridge_or_truth(self):
  r={'e1.value':'An Obscure Novel','r1.template':'The author of {} is','mu.template':'the author of {}','r2.template':'{} was born in the city of','e2.value':'Private Bridge','e3.value':'Private Truth'}
  a,b=render(r);self.assertEqual(a,'The author of An Obscure Novel is');self.assertEqual(b,'The author of An Obscure Novel was born in the city of')
  self.assertNotIn('Private',a+b)

class ReceiptTests(unittest.TestCase):
 def receipt(self):
  from select_dev2 import MODEL,DECODE
  return dict(experiment='E110',phase='deviation2_obscure',verified=True,input_seal_sha256='bank',model_revision=MODEL,decoding=DECODE,filter_gpu_seconds_total=3200,shards=[dict(shard=i,gpu_seconds=800) for i in range(4)])
 def test_new_cap_and_epoch_only(self):
  from select_dev2 import receipt_check
  r=self.receipt();self.assertEqual(len(receipt_check(r,'bank')),4)
  for key,value in [('phase','amendment1'),('filter_gpu_seconds_total',4000),('input_seal_sha256','old')]:
   x=dict(r,**{key:value})
   with self.assertRaises(ValueError):receipt_check(x,'bank')
 def test_completed_subset_only_at_original_cutoff(self):
  from select_dev2 import receipt_check
  r=self.receipt();r.update(shards=r['shards'][:2],filter_gpu_seconds_total=1600,cutoff_reached=True,decision_utc='2026-10-29T14:59:00Z')
  with self.assertRaises(ValueError):receipt_check(r,'bank')
  r['decision_utc']='2026-10-29T15:00:00Z';self.assertEqual(len(receipt_check(r,'bank')),2)
 def test_duplicate_quarter_and_custody_mismatch_rejected(self):
  from select_dev2 import receipt_check
  r=self.receipt();r['shards'][1]['shard']=0
  with self.assertRaises(ValueError):receipt_check(r,'bank')
  r=self.receipt();r['filter_gpu_seconds_total']=3199
  with self.assertRaises(ValueError):receipt_check(r,'bank')

if __name__=='__main__':unittest.main()
