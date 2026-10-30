import unittest,tempfile
from pathlib import Path
import numpy as np
from reader_worker import pipeline,eligible_rows
from analyze_readers_once import rules
class Backend:
 def __init__(self):self.calls=[]
 def load_oracle(self):self.calls.append('oracle')
 def load_nla(self):self.calls.append('nla')
 def validate_tokenization(self,items):self.calls.append('validate')
 def capture(self,items):self.calls.append('capture');return {42:np.zeros((len(items),2)),44:np.zeros((len(items),2))}
 def join(self,v):return np.concatenate(v)
 def take(self,h,ix):return h[ix]
 def save_capture(self,p,h):np.save(p,h)
 def score(self,c,items,h,pairs):self.calls.append(c);return [[0.,1.] for _ in items]
class Budget:
 def call(self,phase,fn,remaining_units=0):return fn()
class ReaderTests(unittest.TestCase):
 def test_parity_failure_prevents_capture(self):
  b=Backend()
  def fail(*args):raise ValueError('parity failed')
  with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):pipeline([],{},b,Budget(),Path(d),None,fail)
  self.assertEqual(b.calls,['oracle'])
 def test_only_registered_channels_after_gate(self):
  b=Backend();items=[{'id':str(i),'feature':'row','split':'test'} for i in range(8)]
  def gate(*args):b.calls.append('gate')
  with tempfile.TemporaryDirectory() as d:pipeline(items,{'rows':{'row':{'olens_descriptive':[['a','b']]*2,'nla':[['a','b']]*2}}},b,Budget(),Path(d),None,gate)
  self.assertLess(b.calls.index('gate'),b.calls.index('capture'));self.assertEqual(b.calls.count('oracle_descriptive'),1);self.assertEqual(b.calls.count('nla'),2)
 def test_cell_miss_excluded(self):
  self.assertEqual(eligible_rows({'rows':[{'row':'r','n':84,'excluded_initial_unknown':0,'median':23,'cell':'long','eligible':False}]}),[])
 def test_false_eligibility_fails(self):
  with self.assertRaises(ValueError):eligible_rows({'rows':[{'row':'r','n':84,'excluded_initial_unknown':0,'median':5,'cell':'short','eligible':True}]})
 def test_rule_and_probe_gate(self):
  m={r:{'probe':.9,'oracle_descriptive':.8 if r in ['fenced_code','latex_list'] else .6} for r in ['fenced_code','latex_list','word_first_piece','number_completion']}
  self.assertEqual(rules(m)['status'],'R1');m['latex_list']['probe']=.84;self.assertEqual(rules(m)['status'],'NOT EVALUABLE')
if __name__=='__main__':unittest.main()
