import unittest
from .booked_bounds248 import project
class BoundsTest(unittest.TestCase):
 def bound(self):return dict(event='settle',id='x',usd='.0086843750',charge_basis='BOOKED_RESERVED_UPPER_BOUND',authority='e34073059',provider_actual_cost_known=False)
 def test_original_bookedbound_not_zero(self):self.assertEqual(project([self.bound()])['total_booked_upper_bound_usd'],'0.0086843750')
 def test_actual_zero_not_rebooked(self):self.assertEqual(project([dict(event='settle',id='z',usd='0'),self.bound()])['total_booked_upper_bound_usd'],'0.0086843750')
 def test_duplicate_bound_rejected(self):
  with self.assertRaises(ValueError):project([self.bound(),self.bound()])
 def test_unknown_authority_rejected(self):
  b=self.bound();b['authority']='other'
  with self.assertRaises(ValueError):project([b])
if __name__=='__main__':unittest.main()
