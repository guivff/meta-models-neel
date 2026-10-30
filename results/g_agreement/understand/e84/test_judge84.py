import unittest
from prepare_judge84 import packetize,candidate_privacy
class Tests(unittest.TestCase):
 def row(self,split='test'):return dict(id='opaque',split=split,files=['/workspace/public/a.py','/workspace/public/b.py'],value='A',file_index=0,label=1,target_path='/workspace/public/a.py')
 def test_exact_paths_and_private_gold(self):
  row=self.row();p,k=packetize([row]);self.assertEqual(p[0]['values'],{'A':row['files'][0],'B':row['files'][1]});self.assertEqual(set(p[0]),{'id','property','values'});self.assertEqual(k[0]['gold'],'A')
 def test_dev_not_judged_and_no_retargeting(self):
  self.assertEqual(packetize([self.row('dev')]),([],[]));r=self.row();r['target_path']=r['files'][1]
  with self.assertRaises(ValueError):packetize([r])
 def test_path_failure_is_hash_only_and_not_rewritten(self):
  r=self.row();p,_=packetize([r]);before=str(p);d=candidate_privacy(p);self.assertEqual(d['failed_candidate_values'],2);self.assertEqual(d['status'],'HOLD_CANDIDATE_PRIVACY');self.assertEqual(str(p),before)
  self.assertNotIn('/workspace',str(d));self.assertTrue(all('candidate_sha256' in x for x in d['failures']))
 def test_no_blanket_absolute_path_exemption(self):
  r=self.row();r['files']=['/repo/a.py','/repo/b.py'];r['target_path']=r['files'][0];p,_=packetize([r]);self.assertEqual(candidate_privacy(p)['status'],'CANDIDATE_ONLY_PASS_FULL_WIRE_PENDING')
if __name__=='__main__':unittest.main()
