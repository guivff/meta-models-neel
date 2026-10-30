import unittest
from .parallel_priority243 import order_slots, initial_refresh

class ParallelPriorityTest(unittest.TestCase):
    def rows(self):
        return [dict(pid=2,bank='E118',own_priority_bank=True),dict(pid=3,bank='E124',own_priority_bank=True),dict(pid=1,bank='E117',own_priority_bank=True)]
    def test_protected_period_keeps_primary_first_before_due(self):
        self.assertEqual(order_slots(self.rows(),1,100,103,1)[0]['pid'],1)
    def test_background_gets_slots_between_primary_sends(self):
        self.assertEqual(order_slots(self.rows(),1,100,101,1)[0]['pid'],2)
    def test_foreign_ticket_is_not_displaced(self):
        r=self.rows();r.insert(0,dict(pid=9,bank='foreign',own_priority_bank=False))
        self.assertEqual([x['pid']for x in order_slots(r,1,100,104,1)],[9,1,2,3])
    def test_missing_primary_does_not_block_ready_work(self):
        self.assertEqual(order_slots(self.rows()[:2],1,0,100,1),self.rows()[:2])
    def test_refresh_preserves_cooldown_counts_future_slot_and_history(self):
        s=dict(interval_seconds=4,next_send_epoch=110,cooldown_until_epoch=90,rate_limits=2,bank_sends={'E117':9})
        r=initial_refresh(s,'direct authority',100)
        self.assertEqual(r['interval_seconds'],1)
        for k in ('next_send_epoch','cooldown_until_epoch','rate_limits','bank_sends'):self.assertEqual(r[k],s[k])
        self.assertEqual(s['interval_seconds'],4)
    def test_refresh_refuses_active_cooldown(self):
        with self.assertRaises(ValueError):initial_refresh(dict(interval_seconds=4,cooldown_until_epoch=101),'direct',100)

if __name__=='__main__':unittest.main()
