import unittest,json
from e82_grouped_judge import candidates,make_records,wire,validate_code

def meta(truth=True):
 return dict(id='ab'*16,belief=['belief value'],belief_aliases=['belief alias'],truth=['truth value']if truth else None,truth_aliases=['truth alias']if truth else [],truth_contrast_eligible=truth,target_kind='property',source_public_id='private-source',reader='oracle',family='fixture')
def render(x,r):return dict(x,rubric=r+json.dumps(x['values']))
def payload(*a):return {'max_tokens':4096,'messages':[{'role':'system','content':a[1]},{'role':'user','content':'[]'}],'response_format':{'schema':'frozen'}}
class Tests(unittest.TestCase):
 def test_full_ragged_positions_retained_twice(self):
  m=meta();g=dict(id=m['id'],positions=[dict(position=i,readout=f'native {i}')for i in range(107)])
  xs,joins=make_records([g],[m],render,'rubric');self.assertEqual(len(xs),2);self.assertTrue(all(x['positions']==g['positions']for x in xs));self.assertEqual({x['target']for x in joins},{'belief','truth'})
 def test_missing_truth_no_fabrication(self):
  m=meta(False);values,targets=candidates(m);self.assertEqual(values['B'],[]);self.assertEqual(targets,{'belief':'A'});xs,j=make_records([dict(id=m['id'],positions=[])],[m],render,'r');self.assertEqual(len(xs),1);self.assertEqual(j[0]['allowed_values'],['A'])
 def test_alias_bytes_retained(self):
  m=meta();v,_=candidates(m);self.assertIn(['belief value','belief alias'],v.values());self.assertIn(['truth value','truth alias'],v.values())
 def test_target_order_independent_of_values(self):
  m=meta();v,t=candidates(m);m['belief']=['new belief'];m['truth']=['new truth'];v2,t2=candidates(m);self.assertEqual(t,t2)
 def test_blind_wire_no_join_fields_or_first_position(self):
  m=meta();xs,_=make_records([dict(id=m['id'],positions=[dict(position=0,readout='native')])],[m],render,'r');w=wire(xs,'r',None,payload);self.assertEqual(w['max_tokens'],4096);data=json.loads(w['messages'][1]['content']);self.assertEqual(set(data[0]),{'id','rubric','positions'});self.assertNotIn('private-source',json.dumps(w));self.assertNotIn('first_position',json.dumps(w))
 def test_evidence_must_be_in_one_native_position(self):
  g=dict(id='id',positions=[dict(readout='part one'),dict(readout='part two')]);code=dict(id='id',category='states_value',values=['A'],evidence='one\npart');self.assertRaises(AssertionError,validate_code,g,code,['A'],lambda *a:None)
 def test_undefined_truth_code_rejected(self):
  g=dict(id='id',positions=[dict(readout='text')]);c=dict(id='id',category='states_value',values=['B'],evidence='text');self.assertRaises(AssertionError,validate_code,g,c,['A'],lambda *a:None)
 def test_silent_allows_no_evidence(self):
  validate_code(dict(id='id',positions=[]),dict(id='id',category='silent',values=[],evidence=''),['A'],lambda *a:None)
if __name__=='__main__':unittest.main()
