import unittest
from source110 import aliases,freeze_templates,PARAPHRASES
from build110 import quotas,sample_rows
from filter110 import EntityIndex,classify,choose
class Tests(unittest.TestCase):
 def test_alias_data_never_executes(self):
  self.assertEqual(aliases("(('A', 'B'),)",'A'),['A','B'])
  with self.assertRaises((ValueError,SyntaxError)):aliases("__import__('os').system('false')",'A')
 def test_longest_alias_and_ambiguity(self):
  i=EntityIndex([('Q1','Paris',['Paris']),('Q2','Paris Texas',['Paris Texas']),('Q3','Other',['Shared']),('Q4','Another',['Shared']),('Q5','Francois',['François'])])
  self.assertEqual(i.match('Paris Texas.'),'Q2');self.assertEqual(i.match('Paris, France.'),'Q1');self.assertIsNone(i.match('Shared.'));self.assertIsNone(i.match('Parisian'));self.assertEqual(i.match('Francois.'),'Q5');self.assertIsNone(i.match('I do not know'));self.assertIsNone(i.match('Paris T',truncated=True))
 def test_exact_floor_and_fallback(self):
  def row(i,stable,native=True,right=False):return dict(candidate_id=str(i),composition_type='type',stable_belief_wrong=stable,native_belief_wrong=native,belief_right=right,twohop_tokens=30)
  self.assertEqual(choose([row(i,True) for i in range(59)])['status'],'NOT_RUN')
  s=choose([row(i,False) for i in range(60)]);self.assertEqual(s['gate'],'no paraphrase gate');self.assertEqual(len(s['wrong']),60)
  s=choose([row(i,True) for i in range(60)]);self.assertEqual(s['gate'],'three_prompt_belief_stability')
 def test_belief_gate_not_twohop_paraphrases(self):
  index=EntityIndex([('Q1','Truth',['Truth']),('Q2','Belief',['Belief']),('Q3','RightAnswer',['RightAnswer']),('Q4','WrongAnswer',['WrongAnswer'])]);item=dict(id='i',composition_type='type',onehop_job_ids=['a','b','c'],twohop_job_id='d',e2_qid='Q1',e3_qid='Q3',twohop_tokens=10)
  outputs={k:dict(raw=v) for k,v in zip('abcd',['Belief','Belief','Belief','WrongAnswer'])}
  c=classify(item,outputs,index);self.assertTrue(c['stable_belief_wrong']);outputs['c']['raw']='Truth';c=classify(item,outputs,index);self.assertTrue(c['native_belief_wrong']);self.assertFalse(c['stable_belief_wrong'])
  outputs['d']['raw']='RightAnswer';self.assertFalse(classify(item,outputs,index)['native_belief_wrong'])
 def test_type_matching_no_reuse(self):
  wrong=[dict(candidate_id=f'w{i}',composition_type='A',stable_belief_wrong=True,native_belief_wrong=True,belief_right=False,twohop_tokens=10+i) for i in range(60)]
  rights=[dict(candidate_id=f'r{i}',composition_type='A' if i<3 else 'B',stable_belief_wrong=False,native_belief_wrong=False,belief_right=True,twohop_tokens=12+i) for i in range(5)]
  s=choose(wrong+rights);self.assertEqual(len(s['right']),3);self.assertEqual(len(s['unmatched_wrong']),57);self.assertEqual(s,choose(list(reversed(wrong+rights))))
 def test_balanced_capped_allocation(self):
  self.assertEqual(quotas({'a':1,'b':100,'c':100},10),{'a':1,'b':5,'c':4});self.assertEqual(sum(quotas({str(i):100 for i in range(52)},3000).values()),3000)
 def test_relation_templates(self):
  self.assertEqual(len(PARAPHRASES),19)
  for templates in PARAPHRASES.values():
   self.assertEqual(len(set(templates)),2)
   for s in templates:self.assertEqual(s.count('{e1}'),1);self.assertNotIn('\n',s)
if __name__=='__main__':unittest.main()
