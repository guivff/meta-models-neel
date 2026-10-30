"""Offline contract tests; no model download, GPU, or E28 scientific score."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C
from analyze import crossed
from worker import attach_lowrank, detach_lowrank


def dev():
    return [{'id': str(i), 'feature': 'prose_paren', 'y': i % 2, 'cluster': str(i // 14)} for i in range(84)]


class Contracts(unittest.TestCase):
    def test_scope_has_all_fourteen_runs(self):
        p = C.validate_plan(C.plan())
        self.assertEqual(len(p['runs']), 14)
        self.assertEqual([x[0] for x in C.RUNS if x[1] == 'S'], ['prose_paren', 'prose_sentiment'])

    def test_scope_cut_rejected(self):
        p = C.plan()
        p['runs'].pop()
        with self.assertRaises(ValueError): C.validate_plan(p)

    def test_targets_whole_original_modules(self):
        m = C.read(C.HERE / 'LORA_TARGETS.json')
        self.assertEqual(m['original_r'], 16)
        self.assertEqual(m['original_lora_alpha'], 32)
        self.assertEqual(m['fresh_rank'], 8)
        self.assertEqual(m['fresh_lora_alpha'], 16)
        self.assertIn('in_proj_qkv', m['target_modules'])
        self.assertIn('down_proj', m['target_modules'])
        self.assertFalse(m['slice_masking'])

    def test_schedule_is_repeatable_and_paired(self):
        l = C.training_schedule(dev(), 'prose_paren', 'L')
        b = C.training_schedule(dev(), 'prose_paren', 'B')
        s = C.training_schedule(dev(), 'prose_paren', 'S')
        self.assertEqual(l, b)
        self.assertEqual((len(l), len(l[0])), (400, 8))
        self.assertEqual([[x['id'] for x in batch] for batch in l], [[x['id'] for x in batch] for batch in s])
        seen = {x['id']: x['y'] for batch in s for x in batch}
        self.assertEqual(sum(seen.values()), 42)
        self.assertNotEqual(seen, {x['id']: x['y'] for x in dev()})
        self.assertEqual({x['phrasing'] for batch in l for x in batch}, {0, 1})

    def test_training_rejects_test_schema(self):
        with self.assertRaises(ValueError):
            C.training_schedule([{'id': str(i), 'feature': 'prose_paren'} for i in range(84)], 'prose_paren', 'L')

    def test_seal_detects_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'x').write_text('frozen')
            C.seal(p)
            C.verify(p)
            (p / 'x').write_text('changed')
            with self.assertRaises(ValueError): C.verify(p)

    def test_cache_location_required(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): C.cache_output(Path(d) / 'ordinary')

    def test_worker_rejects_private_or_unsealed_material(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            C.dump(p / 'provenance.json', {'plan_sha256': C.sha(C.HERE / 'PLAN.json')})
            C.seal(p)
            C.worker_input(p)
            (p / 'test.labels.DO_NOT_STAGE.jsonl').write_text('private')
            with self.assertRaises(ValueError): C.worker_input(p)
            (p / 'test.labels.DO_NOT_STAGE.jsonl').unlink()
            (p / 'unexpected.txt').write_text('extra')
            with self.assertRaises(ValueError): C.worker_input(p)

    def test_worker_rejects_stale_plan_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            C.dump(p / 'provenance.json', {'plan_sha256': '0' * 64})
            C.seal(p)
            with self.assertRaises(ValueError): C.worker_input(p)

    def test_full_forecast_fits(self):
        f = {'pod_count': 1, 'slot': 0, 'plan_sha256': C.sha(C.HERE / 'PLAN.json'),
             'status': 'WARMED_FORECAST', 'forecast_remaining_seconds': 5000,
             'setup_elapsed_seconds': 100, 'elapsed_science_seconds': 0, 'allocated_gpu_seconds': 16637,
             'elapsed_provider_seconds': 200, 'forecast_sha256': 'a' * 64, 'previous_gpu_seconds': 1363}
        a = C.admit([f])
        self.assertEqual(a['status'], 'ADMIT_FULL_GRID')
        self.assertEqual(a['pods'][0]['science_seconds'], 7860)

    def test_forecast_over_cap_refuses_scope_cut(self):
        f = {'pod_count': 1, 'slot': 0, 'plan_sha256': C.sha(C.HERE / 'PLAN.json'),
             'status': 'WARMED_FORECAST', 'forecast_remaining_seconds': 11000,
             'setup_elapsed_seconds': 100, 'elapsed_science_seconds': 0, 'allocated_gpu_seconds': 16637,
             'elapsed_provider_seconds': 200, 'forecast_sha256': 'a' * 64, 'previous_gpu_seconds': 1363}
        self.assertEqual(C.admit([f])['status'], 'NO_FIT_STOP')

    def test_forecast_requires_all_unique_pods(self):
        f = {'pod_count': 2, 'slot': 0, 'plan_sha256': C.sha(C.HERE / 'PLAN.json'),
             'status': 'WARMED_FORECAST', 'forecast_remaining_seconds': 2000,
             'setup_elapsed_seconds': 100, 'elapsed_science_seconds': 0, 'allocated_gpu_seconds': 8318.5,
             'elapsed_provider_seconds': 200, 'forecast_sha256': 'a' * 64, 'previous_gpu_seconds': 1363}
        with self.assertRaises(ValueError): C.admit([f])
        with self.assertRaises(ValueError): C.admit([f, f])
        other = dict(f, slot=1)
        self.assertEqual(C.admit([f, other])['status'], 'ADMIT_FULL_GRID')

    def test_crossing_does_not_impute_unobserved_steps(self):
        self.assertEqual(crossed([.5, .7, .79, .80, .8, .9]), 100)
        self.assertIsNone(crossed([.5] * 6))

    def test_wait_does_not_reset_admission_clock(self):
        self.assertTrue(C.full_scope_still_fits(1000, 5000, 6000, 3900))
        self.assertFalse(C.full_scope_still_fits(1000, 5000, 6000, 4100))
        self.assertFalse(C.full_scope_still_fits(1000, 10000, 5000, 3900))

    def test_assignment_is_full_and_budgeted(self):
        a = {'issuer': 'integrator', 'experiment': 'E28', 'plan_sha256': C.sha(C.HERE / 'PLAN.json'),
             'pod_count': 2, 'slot': 0, 'runs': [list(x) for i, x in enumerate(C.RUNS) if i % 2 == 0],
             'source_published': True, 'external_hardstop_verified': True,
             'target_mapping_sha256': C.sha(C.HERE / 'LORA_TARGETS.json'),
             'allocated_gpu_seconds': 8318.5, 'previous_gpu_seconds': 1363,
             'provider_created_epoch': 1000, 'deadline_epoch': 9318.5}
        C.assignment(a, now=1100)
        bad = dict(a, allocated_gpu_seconds=8319)
        with self.assertRaises(ValueError): C.assignment(bad, now=1100)
        bad = dict(a, previous_gpu_seconds=1)
        with self.assertRaises(ValueError): C.assignment(bad, now=1100)
        bad = dict(a, runs=a['runs'][:-1])
        with self.assertRaises(ValueError): C.assignment(bad, now=1100)
        bad = dict(a, deadline_epoch=float('nan'))
        with self.assertRaises(ValueError): C.assignment(bad, now=1100)
        bad = dict(a, provider_created_epoch=C.PROGRAMME_CUTOFF-500, deadline_epoch=C.PROGRAMME_CUTOFF+1)
        with self.assertRaises(ValueError): C.assignment(bad, now=C.PROGRAMME_CUTOFF-400)


class TorchContracts(unittest.TestCase):
    def test_zero_init_frozen_backbone_trainable_full_modules(self):
        import torch
        from torch import nn
        mapping = C.read(C.HERE / 'LORA_TARGETS.json')
        class Layer(nn.Module):
            def __init__(self):
                super().__init__()
                for name in mapping['target_modules']:
                    setattr(self, name, nn.Linear(4, 4, bias=False))
        model = nn.Module()
        model.model = nn.Module()
        model.model.layers = nn.ModuleList([Layer() for _ in range(64)])
        original = model.model.layers[0].in_proj_qkv
        x = torch.randn(3, 4)
        expected = original(x).detach().clone()
        mounted, params = attach_lowrank(model, mapping)
        actual = model.model.layers[0].in_proj_qkv(x)
        self.assertTrue(torch.equal(actual, expected))
        self.assertFalse(original.weight.requires_grad)
        self.assertEqual(len(mounted), 64 * len(mapping['target_modules']))
        actual.sum().backward()
        self.assertIsNone(original.weight.grad)
        self.assertTrue(any(p.grad is not None and p.grad.abs().sum() > 0 for p in params))
        detach_lowrank(mounted)
        self.assertIs(model.model.layers[0].in_proj_qkv, original)


if __name__ == '__main__':
    unittest.main()
