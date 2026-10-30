import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal
from .accounting250 import add_census
class Tests(unittest.TestCase):
 def test_open_not_queued(self):
  with tempfile.TemporaryDirectory()as t:
   r=Path(t);(r/'E133').mkdir();(r/'E137').mkdir();(r/'E133/ALLOCATION_C.json').write_text(json.dumps(dict(bank='E133',status='OPEN',operator='W-internals-C',reservation_included=True,allocation_usd='5')))
   v=dict(open_banks={},open_caps_remaining_usd='0',actual_plus_open_caps_usd='100')
   with patch('projects.g_agreement.understand.blind_judge.internals_c.accounting250.bank_actual',return_value=(Decimal('.3'),Decimal('.1'))):out=add_census(v,r)
   self.assertEqual(out['actual_plus_open_caps_usd'],'104.6');self.assertNotIn('E137',out['open_banks'])
 def test_no_double_count(self):
  with tempfile.TemporaryDirectory()as t:
   r=Path(t);(r/'E133').mkdir();(r/'E133/ALLOCATION_C.json').write_text(json.dumps(dict(bank='E133',status='OPEN',operator='W-internals-C',reservation_included=True,allocation_usd='5')))
   v=dict(open_banks={'E133':dict(cap='5')},open_caps_remaining_usd='4',actual_plus_open_caps_usd='104');self.assertEqual(add_census(v,r)['actual_plus_open_caps_usd'],'104')
 def test_reject_wrong_cap(self):
  with tempfile.TemporaryDirectory()as t:
   r=Path(t);(r/'E136').mkdir();(r/'E136/ALLOCATION_C.json').write_text(json.dumps(dict(bank='E136',status='OPEN',operator='W-internals-C',reservation_included=True,allocation_usd='5')))
   with self.assertRaises(Exception):add_census(dict(open_banks={},open_caps_remaining_usd='0',actual_plus_open_caps_usd='100'),r)
