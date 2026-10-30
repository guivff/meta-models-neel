import json,unittest
from decimal import Decimal
from unittest.mock import patch
from . import e140_channel258 as channel,transport,resume_e340 as bounds,runner
class Tests(unittest.TestCase):
 def test_real_cap_namespaces_and_cutoff(self):
  with patch.object(channel,'source_gate'):
   with channel.worker('E140'):
    self.assertEqual(transport.CAPS['E140'],Decimal(1));self.assertEqual(bounds.CAPS['E140'],Decimal(1));self.assertEqual(transport.EXPIRY,1793372400)
    self.assertEqual(transport.source_gate(),runner.source_gate())
 def test_original_dual_record_not_envelope_or_scalar(self):
  code=dict(id='0'*32,category='states_value',values=['X','Y','OTHER'],evidence='all')
  self.assertEqual(channel.terminal_record(dict(status='KEPT',result={'records':[code]})),code)
  self.assertIsNone(channel.terminal_record(dict(status='UNPARSEABLE',result=None)))
 def test_readout_only_render_roundtrip(self):
  u=dict(id='0'*32,property='answer to the factual question',values={'X':['whole phrase'],'Y':['東京']},readout='whole phrase')
  a,_=channel.render('E140',u);self.assertEqual(channel.render('E140',json.loads(json.dumps(u,sort_keys=True)))[0],a)
