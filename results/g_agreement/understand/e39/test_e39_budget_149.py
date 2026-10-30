"""§149 operational budget checks, separate from the pod-pinned legacy tests.

Run this file for the 81,000-second cap. Do not edit the legacy test_e39.py or
refresh any running-pod source/analysis seal to add this test-only file.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C


class Budget149(unittest.TestCase):
    def forecasts(self):
        return [{'slot': i, 'pod_count': 6, 'previous_gpu_seconds': 0,
                 'allocated_gpu_seconds': 13500,
                 'plan_sha256': C.sha(C.HERE / 'PLAN.json'),
                 'status': 'WARMED_FORECAST', 'forecast_remaining_seconds': 4000,
                 'setup_elapsed_seconds': 600, 'elapsed_provider_seconds': 1000,
                 'elapsed_science_seconds': 400, 'forecast_sha256': str(i)}
                for i in range(6)]

    def test_registered_cap_and_invalid_plan_budget(self):
        self.assertEqual(C.CAP, 81000)
        C.validate_plan(C.plan())
        plan = C.plan()
        plan['total_gpu_seconds'] = 81001
        with self.assertRaises(ValueError):
            C.validate_plan(plan)

    def test_six_pods_total_81000(self):
        result = C.admit(self.forecasts())
        self.assertEqual(result['status'], 'ADMIT_FULL_GRID')
        self.assertEqual(result['total_experiment_reserved_gpu_seconds'], 81000)

    def test_allocation_above_13500_rejected(self):
        forecasts = self.forecasts()
        forecasts[0]['allocated_gpu_seconds'] = 13501
        with self.assertRaises(ValueError):
            C.admit(forecasts)

    def test_science_cap_unchanged_and_excess_forecast_no_fit(self):
        forecasts = self.forecasts()
        forecasts[0]['forecast_remaining_seconds'] = 7000
        result = C.admit(forecasts)
        self.assertEqual(result['status'], 'ADMIT_FULL_GRID')
        self.assertEqual(result['pods'][0]['science_seconds'], 10800)
        forecasts[0]['forecast_remaining_seconds'] = 11000
        self.assertEqual(C.admit(forecasts)['status'], 'NO_FIT_STOP')

    def test_provider_elapsed_time_is_charged(self):
        forecasts = self.forecasts()
        forecasts[0]['elapsed_provider_seconds'] = 13000
        self.assertEqual(C.admit(forecasts)['status'], 'NO_FIT_STOP')

    def test_missing_slot_rejected(self):
        with self.assertRaises(ValueError):
            C.admit(self.forecasts()[:-1])


if __name__ == '__main__':
    unittest.main()
