import unittest,copy
from prepare62 import *
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from transformers import PreTrainedTokenizerFast
  p=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json');assert sha(p)==TOKENIZER_SHA
  tok=PreTrainedTokenizerFast(tokenizer_file=str(p));cls.enc=staticmethod(lambda s:tok.encode(s,add_special_tokens=False));cls.items=construct(cls.enc);cls.sources=load_sources()
 def test_runner_grid_and_build_checks(self):self.assertEqual(len(validate(self.items,self.enc)),30)
 def test_L0_exact_source_text_tokens_labels(self):
  for x in self.items:
   if x['rung']=='L0':
    old=next(y for y in self.sources[x['source_bank']] if y['id']==x['source_id'])
    for k in ['text','ids','label','value']:self.assertEqual(x[k],old[k])
 def test_asked_twins_exact(self):
  for x in self.items:
   if x['rung']=='L3' and x['state'] in ('S2','S3','S4'):
    old=next(y for y in self.sources['E56'] if y.get('implicit_id')==x['source_id'])
    self.assertEqual(x['text'],old['text']);self.assertEqual(x['ids'],old['ids'])
 def test_L4_answers_single_token(self):
  for x in self.items:
   if x['rung']=='L4':
    self.assertEqual(self.enc(' alpha'),[x['alpha_token_id']]);self.assertEqual(self.enc(' beta'),[x['beta_token_id']]);self.assertTrue(x['text'].endswith('\nReply:'))
 def test_S6_cumulative_cues(self):
  for x in self.items:
   if x['state']=='S6':
    c=int(x['rung'][1:])
    for i,cue in enumerate(CUES[1:],1):self.assertEqual(cue in x['text'],i<=c)
 def test_invalid_capture_boundary_rejected(self):
  items=copy.deepcopy(self.items);items[0]['read_index']=len(items[0]['ids'])
  with self.assertRaises(ValueError):validate(items,self.enc)
if __name__=='__main__':unittest.main()
