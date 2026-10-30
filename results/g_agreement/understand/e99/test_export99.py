import json,tarfile,unittest,hashlib
from pathlib import Path
from collections import Counter
from source99 import HERE,SOURCE,prompt_data
from positions99 import last_sentence,punct_positions,suffix_positions
from other_judges99 import constants,jailbreak,buggy_infer,buggy_grade,agentic_position,agentic_consolidate,agentic_design,compressed_notes,chunk_notes
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.out=HERE/'cache/export_2026-10-28'
  cls.pub=json.loads((cls.out/'CAPTURE_INPUTS.json').read_text());cls.priv=json.loads((cls.out/'ITEMS.PRIVATE.json').read_text())
 def test_source_hashes_and_archive_allowlist(self):
  d=json.loads((HERE/'DELIVERY.json').read_text())
  for p,h in d['files'].items():self.assertEqual(hashlib.sha256((HERE/p).read_bytes()).hexdigest(),h)
  with tarfile.open(d['public_archive']) as tf:self.assertEqual(set(tf.getnames()),{'CAPTURE_INPUTS.json','PLACEBO_SPECS.json'})
  allowed={'id','family','render','rendered_prompt','input_ids','grid_positions','grid_oracle_layers','nla_layer','single_site_position','single_site_oracle_layer','single_site_nla_layer','extra_single_site_positions'}
  for r in self.pub:self.assertEqual(set(r),allowed)
 def test_complete_inventory_and_cells(self):
  self.assertEqual(Counter(r['family'] for r in self.pub),dict(hallucination=149,user_modeling=100,directed_modulation=100,agentic_misalignment=32,jailbreak_recognition=86,buggy_code=49))
  self.assertEqual(len({r['id'] for r in self.pub}),516)
  by_id={r['id']:r for r in self.priv}
  for r in self.pub:
   grid=r['grid_positions'];extra=r['extra_single_site_positions'];self.assertTrue(all(0<=i<len(r['input_ids']) for i in grid+extra))
   if r['family'] in ('directed_modulation','jailbreak_recognition'):
    self.assertEqual(extra,[r['single_site_position']]);self.assertFalse(set(extra)&set(grid))
   else:self.assertIn(r['single_site_position'],grid)
   if r['family']=='hallucination':self.assertEqual(grid,[x['pos'] for x in by_id[r['id']]['source_item']['sites']])
   if r['family']=='jailbreak_recognition':self.assertEqual(grid,punct_positions(by_id[r['id']]['source_item']['read']))
   if r['family']=='agentic_misalignment':self.assertEqual(len(grid),128);self.assertEqual(r['grid_oracle_layers'],[36,44,56])
 def test_placebo_structure(self):
  ps=json.loads((self.out/'PLACEBO_SPECS.json').read_text());real={r['id']:r for r in self.pub}
  self.assertEqual(Counter(r['family'] for r in ps),dict(user_modeling=30,directed_modulation=30,hallucination=30))
  self.assertEqual(len({r['paired_capture_id'] for r in ps}),90)
  for p in ps:
   r=real[p['paired_capture_id']]
   for k in ('grid_positions','extra_single_site_positions','grid_oracle_layers','single_site_position'):self.assertEqual(p[k],r[k])
 def test_position_boundary_examples(self):
  ts=['<|im_start|>','user','Ċ','Hello','.',' New',' request','?','<|im_end|>','Ċ','<|im_start|>','assistant','Ċ']
  self.assertEqual(last_sentence(ts),list(range(5,13)))
  self.assertEqual(suffix_positions(['prefix','Ċ','A',' carrier','.'],'A carrier.'),[2,3,4])
 def test_remaining_prompt_identity_and_dependencies(self):
  for f in ('agentic_misalignment','jailbreak_recognition','buggy_code'):self.assertEqual(constants(f),prompt_data(f)['constants'])
  targets=json.loads((self.out/'AGENTIC_TARGETS.PRIVATE.json').read_text())['items']
  by_id={r['id']:r for r in self.pub}
  for r in self.priv:
   f=r['family'];it=r['source_item']
   if f=='buggy_code':
    self.assertIn('Synthetic description.',buggy_infer('Synthetic description.')['user'])
    self.assertIn(it['code'],buggy_grade(it,'bug','synthetic inference')['user'])
   elif f=='agentic_misalignment':
    self.assertIn('layer 44: example',agentic_position({44:'<explanation>example</explanation>'})['user'])
    self.assertIn('[pos 4] example',agentic_consolidate([(4,'example')])['user'])
    self.assertIn(targets[it['id']]['action'],agentic_design(it,targets[it['id']],'synthetic account')['user'])
   elif f=='jailbreak_recognition':
    p=by_id[r['id']]['grid_positions'][-1];self.assertIn('[1] synthetic',jailbreak(it,p,'synthetic')['user'])
  self.assertEqual(compressed_notes([(1,'uninformative'),(2,'Uninformative.'),(3,'signal')]),[(1,'(positions 1-2 uninformative)'),(3,'signal')])
  self.assertEqual(len(chunk_notes([(1,'a'*100),(2,'b'*100)],20)),2)
if __name__=='__main__':unittest.main()
