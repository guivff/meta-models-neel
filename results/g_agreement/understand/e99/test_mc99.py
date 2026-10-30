import json,unittest
from pathlib import Path
from source99 import HERE,prompt_data
from mc99 import options,render,constants
class Tests(unittest.TestCase):
 def test_templates_and_options(self):
  delivery=json.loads((HERE/'MC_DELIVERY.json').read_text())
  for f,d in delivery.items():
   self.assertEqual(constants(f),prompt_data(f)['constants'])
   records=json.loads(Path(d['private_path']).read_text());items=[r['source_item'] for r in records]
   opts=options(f,items)
   self.assertEqual(len(records),100)
   for r in records:
    o=opts[r['source_item']['id']];self.assertEqual(o['options'],r['options']);self.assertEqual(o['gold_position'],r['gold_position'])
    self.assertEqual(len(r['options']),5)
    call=render(f,r['source_item'],'Synthetic readout.',r['options'])
    self.assertIn('6. cannot tell from the readout',call['user']);self.assertIn('Synthetic readout.',call['user'])
 def test_um_single_pass_substitution(self):
  r=render('user_modeling',{'messages':[{'role':'user','content':'Literal {options_block}'}]},'Literal {cannot}',['a','b','c','d','e'])
  self.assertIn('Literal {options_block}',r['user']);self.assertIn('Literal {cannot}',r['user'])
if __name__=='__main__':unittest.main()
