"""Separate setup/science clocks, with all custody inside the unchanged aggregate."""
import tempfile
import unittest

import channel_contract as C
import worker as W
from test_budget_143 import request, assignment


class Setup146Tests(unittest.TestCase):
    def test_900_outside_unchanged_science_formula(self):
        r = request(32600.)
        self.assertEqual(r['science_cap_seconds'], 49260)
        self.assertEqual(r['setup_allowance_seconds'], 900)
        self.assertEqual(r['maximum_current_allocation_seconds'], 50160)
        self.assertEqual(C.science_cap_seconds(39400.), 59447)
        self.assertEqual(request(39400.)['maximum_current_allocation_seconds'], 60000 - 552.8)

    def test_setup_entry_deadline_is_post_creation(self):
        p, a = assignment(1000.)
        C.validate_assignment(a, p, 1000.)
        with self.assertRaisesRegex(ValueError, 'setup deadline'):
            C.validate_assignment(a, p, 1000.01)
        with tempfile.TemporaryDirectory() as tmp:
            b = W.Budget(a, tmp, clock=lambda: 1000.01, cap_gpu_seconds=60000)
            with self.assertRaisesRegex(ValueError, 'setup deadline'): b.check()

    def test_unused_setup_does_not_extend_science_or_reset_clock(self):
        _, a = assignment(1000.)
        now = [150.]
        with tempfile.TemporaryDirectory() as tmp:
            b = W.Budget(a, tmp, clock=lambda: now[0], cap_gpu_seconds=60000)
            b.start_science()
            self.assertEqual(b.science_deadline, 150 + 1860)
            self.assertLess(b.science_deadline, a['hard_deadline'])
            with self.assertRaisesRegex(ValueError, 'cannot be reset'): b.start_science()
            b.remaining = dict.fromkeys(C.PHASES, 0.)
            now[0] = 1100.  # Setup deadline passed, but science clock is already running.
            self.assertTrue(b.check()['fits'])
            now[0] = 2011.
            with self.assertRaisesRegex(ValueError, 'warm forecast'): b.check()

    def test_full_900_setup_still_keeps_aggregate_and_science_caps(self):
        _, a = assignment(1000.)
        with tempfile.TemporaryDirectory() as tmp:
            b = W.Budget(a, tmp, clock=lambda: 1000., cap_gpu_seconds=60000)
            b.start_science()
            self.assertEqual(b.science_deadline, a['hard_deadline'])
            self.assertEqual(b.science_deadline, 1000 + C.science_cap_seconds(1000.))


if __name__ == '__main__': unittest.main()
