import unittest
from bind_capture import capture_grid,validate_worker_seal,WORKER_SOURCE_SHA,PUBLIC_ITEMS_SHA
def fixtures():
 public=[dict(item_id=str(i),split='dev'if i<3360 else'test',input_ids=[7,8],read_position=1)for i in range(6720)]
 labels=[dict(item_id=x['item_id'],split=x['split'])for x in public]
 order=[x['item_id']for x in public]
 positions=[dict(item_id=i,read_position=1)for i in order]
 return public,labels,order,positions
class Tests(unittest.TestCase):
 def worker(self):return dict(experiment='E97',version=2,status='COMPLETE',reader_outputs=0,reader_outputs_opened=False,source_seal_sha256=WORKER_SOURCE_SHA,public_items_sha256=PUBLIC_ITEMS_SHA,files={x:'sha'for x in ['acts42.npy','acts44.npy','items.order.json','CAPTURE_STARTED.json']})
 def test_worker_valid(self):validate_worker_seal(self.worker())
 def test_worker_incomplete(self):
  s=self.worker();s['status']='NO_FIT'
  with self.assertRaises(ValueError):validate_worker_seal(s)
 def test_worker_failure_evidence(self):
  s=self.worker();s['files']['FAILURE.json']='sha'
  with self.assertRaises(ValueError):validate_worker_seal(s)
 def test_worker_wrong_source(self):
  s=self.worker();s['source_seal_sha256']='other'
  with self.assertRaises(ValueError):validate_worker_seal(s)
 def test_full(self):self.assertEqual(len(capture_grid(*fixtures())[2]),3360)
 def test_test_only(self):
  p,l,o,r=fixtures();self.assertEqual(len(capture_grid(p,l,o[3360:],r[3360:])[2]),3360)
 def test_missing(self):
  p,l,o,r=fixtures()
  with self.assertRaises(ValueError):capture_grid(p,l,o[:-1],r[:-1])
 def test_wrong_token(self):
  p,l,o,r=fixtures();r[0]['read_position']=0
  with self.assertRaises(ValueError):capture_grid(p,l,o,r)
 def test_reordered_metadata(self):
  p,l,o,r=fixtures();r[0],r[1]=r[1],r[0]
  with self.assertRaises(ValueError):capture_grid(p,l,o,r)
if __name__=='__main__':unittest.main()
