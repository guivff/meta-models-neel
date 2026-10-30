import unittest,types
from decimal import Decimal
from .e135_channel245 import make_units,enforce
from .e128_channel import original104_call
from .transport import SHARED
class E135Test(unittest.TestCase):
 def fixture(self):
  old=[dict(item_id='original',arm='U',row='fact_recall',reader='oracle',condition='steered',flipped=True,target='A',property='location',values={'A':['new'],'B':['old']})];items=[dict(id=c,base_id='b',alpha=6,condition=c,row='fact_recall')for c in('steered','random')];ptr=[dict(id=c,original_base_id='original',scale=.75)for c in('steered','random')];lab=[dict(original_base_id='original',new_value='new',old_value='old')];records=[(dict(member='test',keys=[i,'text']),dict(id=c+str(l),item_id=c,base_id='b',alpha=6,condition=c,source_layer=l,reader='oracle',text=''))for i,(c,l)in enumerate((c,l)for c in('steered','random')for l in(44,52))];rubric=(SHARED/'E104/blind/RUBRIC.md').read_text();return records,old,ptr,items,lab,rubric
 def test_full_control_grid_empty_readouts_retained(self):
  u,j=make_units(*self.fixture(),nitems=1);self.assertEqual(len(u),4);self.assertTrue(all(x['data']['readout']==''for x in u));self.assertEqual({x['dose']for x in j},{6})
 def test_wrong_dose_rejected(self):
  a=self.fixture();a[0][0][1]['alpha']=4
  with self.assertRaises(Exception):make_units(*a,nitems=1)
 def test_missing_control_rejected(self):
  a=self.fixture();a[0].pop()
  with self.assertRaises(Exception):make_units(*a,nitems=1)
 def test_duplicate_identity_rejected(self):
  a=self.fixture();a[0].append(a[0][0])
  with self.assertRaises(Exception):make_units(*a,nitems=1)
 def test_original_candidate_orientation_checked(self):
  a=self.fixture();a[4][0]['new_value']='old'
  with self.assertRaises(Exception):make_units(*a,nitems=1)
 def test_wire_unit_contains_only_blind_fields(self):
  u,j=make_units(*self.fixture(),nitems=1);self.assertEqual(set(u[0]['data']),{'id','property','values','readout'});self.assertTrue(all('condition'not in x['data']for x in u))
 def test_private_metadata_rejected_by_original_renderer(self):
  u,j=make_units(*self.fixture(),nitems=1);u[0]['data']['condition']='steered'
  with self.assertRaises(Exception):original104_call(u[0],None)
 def test_actual_namespace_cap1_after_reload(self):
  n={'CAP':Decimal(5)};exec('class Ledger:\n def reserve(self,x):return x<=CAP\n def settle(self,x):return x<=CAP\n def summary(self):return {"cap_usd":str(CAP)}\ndef one(client):return CAP\n',n);a=types.SimpleNamespace(CAP=Decimal(5));c=types.SimpleNamespace(ledger=n['Ledger']());enforce(a,c,n['one']);self.assertFalse(c.ledger.reserve(Decimal('1.01')));n['CAP']=Decimal(5);enforce(a,c,n['one']);self.assertEqual(n['one'](c),Decimal(1))
 def test_wire_count_validator_checks_actual_saved_calls(self):
  from .e135_channel245 import validate_plan
  p=[dict(unit=dict(id='u'),calls=['a','b','c'])];c=[dict(id=i)for i in ['a','b','c']];self.assertEqual(validate_plan(p,c,1)['physical_wire_upper_count'],3)
 def test_missing_retry_wire_is_rejected(self):
  from .e135_channel245 import validate_plan
  with self.assertRaises(Exception):validate_plan([dict(unit=dict(id='u'),calls=['a','b','c'])],[dict(id=i)for i in ['a','b']],1)
if __name__=='__main__':unittest.main()
