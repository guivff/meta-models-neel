import json,unittest
from .e136_channel250 import cue_call as prepared,QUESTIONS
from .e136_dispatch251 import cue_call
class Tests(unittest.TestCase):
 def test_original_wire_roundtrip(self):
  for q in QUESTIONS.values():
   u=dict(id='opaque',readout='literal readout',source_text='exact original source',question=q)
   loaded=json.loads(json.dumps(u,sort_keys=True));self.assertEqual(cue_call(loaded)[0],prepared(u)[0])
 def test_no_private_fields(self):
  u=dict(id='opaque',readout='',source_text='',question=QUESTIONS['misuse_intent'],label=1)
  with self.assertRaises(Exception):cue_call(u)
 def test_same_validator(self):
  u=dict(id='opaque',readout='pressing an answer',source_text='',question=QUESTIONS['sycophancy_pressure']);cue_call(u)[1](dict(code='YES',evidence='pressing an answer'))
