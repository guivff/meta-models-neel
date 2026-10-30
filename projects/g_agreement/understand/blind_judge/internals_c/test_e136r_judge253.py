import unittest,json
from .e136r_judge253 import readout_call,assert_readout_only,QUESTIONS
from projects.g_agreement.e136_named import named
class Tests(unittest.TestCase):
 def unit(self,cue='sycophancy_pressure'):return dict(id='0'*32,readout='The user insists on a particular answer.',cue=cue)
 def test_payload_only_readout_id_question_both_cues(self):
  for cue in QUESTIONS:
   u=self.unit(cue);c,_=readout_call(u);self.assertEqual(json.loads(c['rendered']['user']),dict(id=u['id'],readout=u['readout']));self.assertEqual(c['rendered']['system'],named.SYSTEM+'\nQuestion: '+QUESTIONS[cue]);self.assertTrue(assert_readout_only(c,u))
 def test_reject_source_prompt_and_all_private_fields(self):
  for key in ['source_text','source_prompt','prompt','messages','label','split','probe','source_id','condition','answer','truth']:
   u=self.unit();u[key]='forbidden'
   with self.assertRaises(Exception):readout_call(u)
 def test_roundtrip_stable(self):
  u=self.unit();self.assertEqual(readout_call(u)[0],readout_call(json.loads(json.dumps(u,sort_keys=True)))[0])
 def test_empty_is_retained(self):
  u=self.unit();u['readout']='';self.assertEqual(json.loads(readout_call(u)[0]['rendered']['user'])['readout'],'')
 def test_codes(self):
  _,v=readout_call(self.unit());v(dict(code='YES',evidence='insists'));v(dict(code='NO',evidence=''));v(dict(code='UNPARSEABLE',evidence=''))
 def test_detect_modified_wire(self):
  u=self.unit();c,_=readout_call(u);d=json.loads(c['rendered']['user']);d['source_text']='secret';c['rendered']['user']=json.dumps(d)
  with self.assertRaises(Exception):assert_readout_only(c,u)
