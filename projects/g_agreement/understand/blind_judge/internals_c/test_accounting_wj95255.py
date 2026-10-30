import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal
from .accounting_wj95255 import add_e95
from projects.g_agreement.readerbench.io import write
class Tests(unittest.TestCase):
 def test_open_lifetime_remaining_not_doublecounted(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);write(root/'ALLOCATION_WJ95.json',dict(status='OPEN',experiment='E95',operator='W-judge95',reservation_included=True,allocation_usd='60',lifetime_maximum_usd='60',per_stage_reset=False,ledger_root=str(root/'ledger')))
   o=dict(open_banks={},open_caps_remaining_usd='150',actual_plus_open_caps_usd='235')
   with patch('projects.g_agreement.understand.blind_judge.internals_c.accounting_wj95255.bank_actual',return_value=(Decimal(2),Decimal(3))):
    add_e95(o,root);self.assertEqual(o['actual_plus_open_caps_usd'],'290');self.assertEqual(o['open_banks']['E95']['open_usd'],'55');add_e95(o,root);self.assertEqual(o['actual_plus_open_caps_usd'],'290')
 def test_queued_absent_not_open(self):
  with tempfile.TemporaryDirectory()as d:
   o=dict(open_banks={});self.assertEqual(add_e95(o,Path(d)),o)
 def test_stage_reset_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);write(root/'ALLOCATION_WJ95.json',dict(status='OPEN',experiment='E95',operator='W-judge95',reservation_included=True,allocation_usd='60',lifetime_maximum_usd='60',per_stage_reset=True,ledger_root=str(root/'ledger')))
   with self.assertRaises(Exception):add_e95(dict(open_banks={}),root)
