import unittest
from forecast_adapter import require_scope
def fixtures():
 rows=['r'+str(i)for i in range(40)]
 p=dict(experiment='E97',layer=44,split='test',units=[dict(id=r,source_row=r,binary=True,item_ids=list(range(84)))for r in rows])
 r=dict(experiment='E97',issuer='integrator',status='VERIFIED_CAPTURE_ONLY',reviewer_correction_passed=True,reviewer_correction_receipt_sha256='reviewproof',original_bank_seal_sha256='2afa89f0e551274b82368075338f7b117dcbbe97b403bf4a29d0a6b442ea4f08',reader_outputs_opened_at_registration=False,reader_outputs_opened_before_forecast=False,readers_held_until_forecast_commit=True)
 return p,r,rows
class Tests(unittest.TestCase):
 def test_valid(self):require_scope(*fixtures())
 def test_review_hold(self):
  p,r,rows=fixtures();r['reviewer_correction_passed']=False
  with self.assertRaises(ValueError):require_scope(p,r,rows)
 def test_old_bank(self):
  p,r,rows=fixtures();r['original_bank_seal_sha256']='32b3c4d1a116dae67c00fe9642bac68047a00477040eefef528962485d1ddfab'
  with self.assertRaises(ValueError):require_scope(p,r,rows)
 def test_already_open(self):
  p,r,rows=fixtures();r['reader_outputs_opened_before_forecast']=True
  with self.assertRaises(ValueError):require_scope(p,r,rows)
 def test_missing_property(self):
  p,r,rows=fixtures();p['units'].pop()
  with self.assertRaises(ValueError):require_scope(p,r,rows)
if __name__=='__main__':unittest.main()
