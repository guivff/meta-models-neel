import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run_once as R
A,C=R.module()
from projects.g_agreement.e73.test_analyze_controls import grids
class AnalysisAdapterTests(unittest.TestCase):
 def test_no_exclusions_equal_frozen(self):
  a,b=grids();self.assertEqual(R.sensitivity(a,b,[set(),set()],A,C)['R_W1'],C.compute(a,b)['R_W1'])
 def test_exclusion_changes_denominator_not_other_records(self):
  a,b=grids();old=copy.deepcopy((a,b));uid=b[0][0]['opaque_id'];r=R.sensitivity(a,b,[set(),{uid}],A,C)
  row=r['readers']['oracle']['states']['W7'];self.assertEqual(row['n_readouts'],199);self.assertEqual(row['redaction_excluded'],1);self.assertEqual(row['correct_only'],59);self.assertEqual(r['readers']['oracle']['judgment_missingness']['total'],1399);self.assertEqual((a,b),old)
 def test_once_claim_precedes_any_outcome_read(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'already';out.mkdir()
   with patch.object(R,'checked_plan',return_value={'output':str(out)}),patch.object(R,'adapt_bank',side_effect=AssertionError('outcomes')):
    with self.assertRaises(FileExistsError):R.run({})
 def test_bad_plan_hash_before_outcomes(self):
  with self.assertRaises(Exception):R.checked_plan({'commit':'c06ae1b7','path':'projects/g_agreement/e73/analyze.py','sha256':'0'*64})
