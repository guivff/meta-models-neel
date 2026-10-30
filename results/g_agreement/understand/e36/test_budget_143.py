"""CPU-only §143 custody and single-pod deadline tests."""
import copy
import unittest

import channel_contract as C
from test_channel_contract import plan, expanded_scope, expanded_rules


def bound_plan():
    return plan(expanded_scope(), expanded_rules())


def request(forecast, prior=552.8):
    phases = dict.fromkeys(C.PHASES, 0.)
    phases['parity'] = 100.
    phases['capture'] = forecast - 100.
    return C.make_launch_request(bound_plan(), plan_path='p.json', assignment_path='a.json',
            assets_path='assets.json', repository_root='/synthetic/repo', output_path='/synthetic/out',
            prior_gpu_seconds=prior, phase_estimates_seconds=phases)


def assignment(forecast=8000.):
    p, r = bound_plan(), request(forecast)
    deadline = 100. + r['maximum_current_allocation_seconds']
    a = {'operator': 'integrator', 'experiment': 'E36', 'plan_sha256': p['plan_sha256'],
         'gpu_count': 1, 'gpu_type': 'H200', 'pod_id': 'synthetic', 'prior_gpu_seconds': 552.8,
         'allocation_started_at': 100., 'hard_deadline': deadline,
         'phase_estimates_seconds': r['phase_estimates_seconds'], 'warmed_forecast_seconds': forecast,
         'warmed_forecast_verified': True, 'warmed_forecast_receipt': 'synthetic-only',
         'external_stop': {'confirmed': True, 'deadline': deadline, 'receipt': 'synthetic-only'}}
    return p, a


class Budget143Tests(unittest.TestCase):
    def test_aggregate_and_forecast_caps(self):
        r = request(8000.)
        self.assertEqual(r['aggregate_cap_gpu_seconds'], 60000)
        self.assertEqual(r['maximum_current_allocation_seconds'], 13260)
        self.assertEqual(request(32600.)['maximum_current_allocation_seconds'], 50160)
        self.assertEqual(request(39400.)['maximum_current_allocation_seconds'], 59447.2)
        self.assertEqual(request(1000., 58000.)['maximum_current_allocation_seconds'], 2000)

    def test_cannot_reset_prior_custody_or_outgrow_pod_cap(self):
        with self.assertRaisesRegex(ValueError, '552.8'): request(1000., 0)
        with self.assertRaisesRegex(ValueError, 'cannot fit'): request(40000.)
        with self.assertRaisesRegex(ValueError, 'cannot fit'): request(1000., 59000.)

    def test_runtime_checks_pod_deadline_and_warmed_receipt(self):
        p, a = assignment()
        C.validate_assignment(a, p, 100.)
        bad = copy.deepcopy(a)
        bad['hard_deadline'] += 1
        bad['external_stop']['deadline'] = bad['hard_deadline']
        with self.assertRaisesRegex(ValueError, 'per-pod cap'): C.validate_assignment(bad, p, 100.)
        bad = copy.deepcopy(a)
        bad['warmed_forecast_verified'] = False
        with self.assertRaisesRegex(ValueError, 'warmed forecast receipt'): C.validate_assignment(bad, p, 100.)
        bad = copy.deepcopy(a)
        bad['warmed_forecast_seconds'] += 1
        with self.assertRaisesRegex(ValueError, 'full-pod warmed'): C.validate_assignment(bad, p, 100.)

    def test_single_pod_above_old_shard_ceiling_and_new_upper_boundary(self):
        p, a = assignment(32600.)
        self.assertEqual(a['hard_deadline'] - a['allocation_started_at'], 50160)
        C.validate_assignment(a, p, 100.)
        p, a = assignment(39400.)
        C.validate_assignment(a, p, 100.)
        a['hard_deadline'] += .1
        a['external_stop']['deadline'] = a['hard_deadline']
        with self.assertRaisesRegex(ValueError, 'aggregate cap'): C.validate_assignment(a, p, 100.)

    def test_single_pod_only_and_unchanged_science(self):
        p, a = assignment()
        self.assertEqual(p['pod_budget']['max_pods'], 1)
        self.assertFalse(p['pod_budget']['row_sharding'])
        self.assertEqual(p['item_count'], 4200)
        self.assertEqual(p['parity_threshold'], .02)
        self.assertEqual(p['channels'], C.CHANNELS)
        a['gpu_count'] = 2
        with self.assertRaisesRegex(ValueError, 'one sequential GPU'): C.validate_assignment(a, p, 100.)


if __name__ == '__main__': unittest.main()
