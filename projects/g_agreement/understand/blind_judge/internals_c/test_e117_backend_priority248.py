import unittest,tempfile,os
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
from . import e117_backend_priority248 as p
from projects.g_agreement.readerbench.io import write,read
class ProtectedPacingTest(unittest.TestCase):
 def test_own_ticket_promotion_keeps_shared_rate_state(self):
  with tempfile.TemporaryDirectory()as td:
   r=Path(td);(r/'cache/g_agreement/understand/internals_c/parallel_priority243').mkdir(parents=True);write(r/'cache/g_agreement/understand/internals_c/parallel_priority243/POLICY.json',dict(own_active_banks=['E117','E118']));s=dict(interval_seconds=1,next_send_epoch=100,cooldown_until_epoch=0,rate_limits=7,bank_sends={'E117':9},waiting=[dict(ticket='background',pid=123,bank='E118')]);write(r/'THROUGHPUT.json',s)
   @contextmanager
   def lock():yield
   with patch.object(p,'SHARED',r),patch.object(p.transport,'ROOT',r),patch.object(p.transport,'unpaused'),patch.object(p.parallel_funded,'pacing_lock',lock),patch.object(p.os,'kill'),patch.object(p.time,'time',return_value=100),patch.object(p,'LAST_SEND',0),patch.object(p,'write',side_effect=lambda path,value:write(path,value)if Path(path)==r/'THROUGHPUT.json'else None):p.claim_slot('E117')
   v=read(r/'THROUGHPUT.json');self.assertEqual(v['interval_seconds'],1);self.assertEqual(v['cooldown_until_epoch'],0);self.assertEqual(v['rate_limits'],7);self.assertEqual(v['bank_sends']['E117'],10);self.assertEqual(v['waiting'][0]['ticket'],'background')
 def test_foreign_not_displaced(self):
  r=[dict(pid=99,bank='foreign',own_priority_bank=False),dict(pid=2,bank='E118',own_priority_bank=True),dict(pid=1,bank='E117',own_priority_bank=True)];self.assertEqual([x['pid']for x in p.order_slots(r,1,0,100,1)],[99,1,2])
 def test_other_bank_cannot_use_priority_claim(self):
  with self.assertRaises(ValueError):p.claim_slot('E118')
if __name__=='__main__':unittest.main()
