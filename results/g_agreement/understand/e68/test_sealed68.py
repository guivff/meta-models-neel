import unittest,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
class SealTests(unittest.TestCase):
 def test_hashes(self):
  for p,h in load(HERE/'POSITION_SEAL.json')['files'].items():self.assertEqual(hashlib.sha256((HERE/p).read_bytes()).hexdigest(),h)
 def test_ratified_anchors_unchanged(self):
  old={x['id']:x for x in load(HERE/'POSITIONS_DRAFT.json')['items']}
  xs=load(HERE/'POSITIONS.json')['items'];self.assertEqual(len(xs),336)
  for x in xs:
   for key in ('positions','gap','append_suffix','source_prefix_sha256'):self.assertEqual(x[key],old[x['id']][key])
   self.assertEqual(x['dropped'],x['row']=='arith_compare')
  self.assertEqual(sum(not x['dropped'] for x in xs),252)
 def test_capture_and_labels(self):
  xs=load(HERE/'cache/ratified_2026-10-27/INPUTS.json');ys={x['id']:x for x in load(HERE/'cache/ratified_2026-10-27/LABELS.PRIVATE.json')}
  self.assertEqual(len(xs),252)
  for x in xs:
   self.assertNotIn('label',x);self.assertNotIn('value',x)
   a,b,c=[x['positions'][k] for k in ('P_far','P_mid','P_pre')]
   self.assertTrue(0<=a<b<c<len(x['ids']));self.assertEqual(c,len(x['ids'])-1);self.assertEqual(b,(a+c)//2)
  for row in ('container_after_move','holder_after_handovers','topic_twin'):
   group=[x for x in xs if x['feature']==row];self.assertEqual(len(group),84);self.assertEqual(sum(ys[x['id']]['label'] for x in group),42)
 def test_request(self):
  req=load(HERE/'LAUNCH_REQUEST.json');self.assertEqual(req['position_seal_sha256'],hashlib.sha256((HERE/'POSITION_SEAL.json').read_bytes()).hexdigest());self.assertEqual(req['gpu_cap_seconds'],2160)
  self.assertEqual(req['archive_sha256'],hashlib.sha256(Path(req['archive_path']).read_bytes()).hexdigest())
if __name__=='__main__':unittest.main()
