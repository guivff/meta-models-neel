"""CPU-only synthetic checks; no target model, real labels or scores loaded."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common58 import ARMS, CONTROLS, SHALLOW
from math58 import aggregate, check_basis, PCAMoments, projection_hook, random_basis
import cpu_join58 as L
import worker58 as W
from worker58 import Backend


class ProjectionTests(unittest.TestCase):
    def test_prompt_positions_only_variable_lengths_and_tuple(self):
        q = torch.eye(4)[:, :2]
        h = torch.arange(24).reshape(2, 3, 4).to(torch.bfloat16)
        hook = projection_hook(q, [1, 2])
        output = hook(None, None, (h, 'preserve auxiliary output'))
        actual = output[0]
        self.assertEqual(output[1], 'preserve auxiliary output')
        self.assertEqual(actual.dtype, h.dtype)
        self.assertTrue(torch.equal(actual[0, 1:], h[0, 1:]))
        self.assertTrue(torch.equal(actual[1, 2:], h[1, 2:]))
        self.assertTrue(torch.equal(actual[0, 0, :2], torch.zeros(2, dtype=h.dtype)))
        self.assertTrue(torch.equal(actual[1, :2, :2], torch.zeros((2, 2), dtype=h.dtype)))
        self.assertTrue(torch.equal(actual[..., 2:], h[..., 2:]))

    def test_projection_idempotent_and_zero_exact(self):
        q = torch.from_numpy(random_basis(1, dim=8, rank=3))
        h = torch.randn(2, 4, 8)
        hook = projection_hook(q, [4, 4])
        one = hook(None, None, h)
        self.assertTrue(torch.allclose(hook(None, None, one), one, atol=1e-6))
        self.assertTrue(torch.equal(projection_hook(torch.zeros_like(q), [4, 4])(None, None, h), h))

    def test_random_seed_and_orthonormality(self):
        a, b = random_basis(1, 8, 3), random_basis(2, 8, 3)
        self.assertTrue(np.array_equal(a, random_basis(1, 8, 3)))
        self.assertFalse(np.array_equal(a @ a.T, b @ b.T))
        self.assertLess(check_basis(a, 8, 3), 1e-5)
        with self.assertRaises(ValueError):
            check_basis(np.ones((8, 3)), 8, 3)

    def test_pca_centered_top_directions(self):
        x = torch.tensor([[10., 0., 99.], [-10., 0., 99.], [0., 3., 99.], [0., -3., 99.]])
        m = PCAMoments(3, 'cpu'); m.add(x[:2]); m.add(x[2:])
        q, eigen = m.basis(2)
        self.assertEqual(m.n, 4)
        self.assertTrue(torch.allclose(q.abs(), torch.eye(3)[:, :2]))
        self.assertEqual(eigen, [200., 18.])

    def test_pca_rejects_rank_completion(self):
        m = PCAMoments(3, 'cpu'); m.add(torch.ones(4, 3))
        with self.assertRaises(ValueError):
            m.basis(2)


class ToyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer = torch.nn.Identity()
        self.embed = torch.nn.Embedding(11, 4)
        self.head = torch.nn.Linear(4, 11, bias=False)
        generator = torch.Generator().manual_seed(10)
        with torch.no_grad():
            self.embed.weight.copy_(torch.randn(11, 4, generator=generator))
            self.head.weight.copy_(torch.randn(11, 4, generator=generator))

    def forward(self, input_ids, attention_mask, logits_to_keep, use_cache, position_ids=None):
        from types import SimpleNamespace
        h = self.layer((self.embed(input_ids) * attention_mask[:, :, None]).cumsum(1))
        selection = slice(-logits_to_keep, None) if isinstance(logits_to_keep, int) else logits_to_keep
        return SimpleNamespace(logits=self.head(h)[:, selection])


class ScoringTests(unittest.TestCase):
    def test_summed_candidate_likelihood_offsets_and_padding(self):
        backend = Backend.__new__(Backend)
        backend.model = ToyModel(); backend.layer = backend.model.layer; backend.device = 'cpu'
        items = [{'ids': [2, 3], 'pairs': [{'A_ids': [4], 'B_ids': [5, 6]}]},
                 {'ids': [1], 'pairs': [{'A_ids': [2, 3], 'B_ids': [4]}]}]
        actual = backend.score([(x, 0) for x in items])
        expected = []
        for x in items:
            values = []
            for key in ('A_ids', 'B_ids'):
                candidate = x['pairs'][0][key]; tokens = x['ids'] + candidate
                ids = torch.tensor([tokens]); mask = torch.ones_like(ids)
                out = backend.model(ids, mask, torch.arange(len(tokens)), False).logits[0].log_softmax(-1)
                values.append(sum(float(out[len(x['ids']) - 1 + j, token].detach()) for j, token in enumerate(candidate)))
            expected.append(tuple(values))
        np.testing.assert_allclose(actual, expected, atol=1e-6)
        self.assertEqual(actual, backend.score([(x, 0) for x in items], torch.zeros(4, 2)))
        self.assertEqual(len(backend.layer._forward_hooks), 0)


def grid(main_pass=7, control_pass=2):
    rows, records = [], []
    for i, feature in enumerate(list(CONTROLS) + ['main' + str(i) for i in range(10)]):
        control = i < 3
        row = {'key': feature, 'feature': feature, 'control': control,
               'category': 'content' if control else 'bookkeeping',
               'test': [{'id': feature + ':0', 'label': 1, 'pairs': [{}, {}]}]}
        rows.append(row)
        j_damage = (4. if i < control_pass else 3.) if control else (2.5 if i - 3 < main_pass else 3.)
        for pair_index in range(2):
            for arm in ARMS:
                value = 8. if arm == 'none' else 8. - j_damage if arm == 'J' else 9. if arm == 'PCA' else 6.
                records.append({'row': feature, 'id': feature + ':0', 'pair_index': pair_index,
                                'arm': arm, 'logodds_A_minus_B': value})
    return rows, records


class RuleTests(unittest.TestCase):
    def test_registered_inclusive_boundaries_and_pca_retention(self):
        rows, records = grid()
        result = aggregate(rows, records)
        self.assertTrue(result['R_b1']['met'])
        self.assertTrue(result['R_b2']['met'])
        self.assertEqual(result['R_b2']['passing'], 7)
        self.assertEqual(len(result['PCA_rows_reported_without_exclusion']), 13)

    def test_sanity_failure_prevents_r2_verdict(self):
        result = aggregate(*grid(control_pass=1))
        self.assertFalse(result['R_b1']['met'])
        self.assertIsNone(result['R_b2']['met'])
        self.assertEqual(result['R_b2']['status'], 'NOT EVALUABLE')

    def test_r2_below_70_percent(self):
        self.assertFalse(aggregate(*grid(main_pass=6))['R_b2']['met'])

    def test_missing_duplicate_extra_and_nonfinite(self):
        rows, records = grid()
        for bad in (records[:-1], records + [records[-1]],
                    records + [{**records[-1], 'id': 'unknown'}],
                    [{**records[0], 'logodds_A_minus_B': float('nan')}] + records[1:]):
            with self.assertRaises(ValueError):
                aggregate(rows, bad)

    def test_signed_orientation_pair_and_item_average(self):
        rows, records = grid()
        modified = copy.deepcopy(records)
        rows[0]['test'][0]['label'] = 0
        for r in modified:
            if r['row'] == rows[0]['key']:
                r['logodds_A_minus_B'] *= -1
        self.assertEqual(aggregate(rows, modified)['rows'][0]['damage']['J'], 4.)

    def test_missing_control_stops(self):
        rows, records = grid()
        removed = rows[0]['key']
        with self.assertRaises(ValueError):
            aggregate(rows[1:], [r for r in records if r['row'] != removed])

    def test_random_mean_over_seeds_is_signed(self):
        rows, records = grid()
        for r in records:
            if r['arm'].startswith('random'):
                # Damage ranges from -2 to +2; the registered mean is zero.
                r['logodds_A_minus_B'] = 8. - (int(r['arm'][-1]) - 2)
        self.assertEqual(aggregate(rows, records)['rows'][0]['random_damage_mean5'], 0.)
        self.assertIsNone(aggregate(rows, records)['rows'][0]['J_over_random_damage'])

    def test_shallow_ratios_descriptive_only(self):
        rows, records = grid()
        for name in SHALLOW:
            row = {'key': name, 'feature': name, 'control': False, 'category': 'content',
                   'test': [{'id': name + ':0', 'label': 1, 'pairs': [{}]}]}
            rows.append(row)
            for arm in ARMS:
                value = 8. if arm == 'none' else 6. if arm.startswith('random') else 5.
                records.append({'row': name, 'id': name + ':0', 'pair_index': 0, 'arm': arm,
                                'logodds_A_minus_B': value})
        result = aggregate(rows, records)
        self.assertEqual(len(result['shallow_content_group_descriptive']), 2)
        self.assertEqual(result['shallow_content_group_descriptive'][0]['J_over_random_damage'], 1.5)
        self.assertEqual(result['R_b2']['denominator'], 10)


def bank_fixture(n=10):
    rows = []
    banks = ['W1', 'E36', 'E56', 'E57', 'E49']
    for i in range(n):
        feature = CONTROLS[i] if i < 3 else SHALLOW[i - 3] if i < 5 else 'main' + str(i)
        row = {'key': banks[i % 5] + '/' + feature, 'bank': banks[i % 5], 'feature': feature,
               'category': 'content' if i < 3 else 'bookkeeping', 'control': i < 3}
        for split in ('dev', 'test'):
            row[split] = [{'id': feature + ':' + split + ':' + str(j), 'split': split, 'ids': [2, 3],
                'label': int(j < 42), 'pairs': [{'A_ids': [4], 'B_ids': [5], 'source_sha256': '0' * 64}]}
                         for j in range(84)]
        if row['bank'] == 'E57':
            for j, x in enumerate(row['test']):
                x['swap_donor_id'] = row['test'][(j + 42) % 84]['id']
        rows.append(row)
    return {'experiment': 'E58b', 'complete_registered_scope': True, 'definition_holds_resolved': True,
            'pca_population': W.pca_population(rows), 'definition_authority_commit': 'a8a25b66', 'rows': rows,
            'source_seals': {'source.json': '0' * 64}, 'category_seal_sha256': '0' * 64,
            'pair_inventory': [{'row': r['key'], 'status': 'APPLICABLE'} for r in rows]}


class BindingTests(unittest.TestCase):
    def test_swap_reuses_exact_opposite_prompt_scores(self):
        bank = bank_fixture(); row = next(r for r in bank['rows'] if r['bank'] == 'E57')
        # aggregate() requires the complete sanity set; supply all bank rows.
        records = []
        for r in bank['rows']:
            for x in r['test']:
                for arm in ARMS:
                    records.append({'row': r['key'], 'id': x['id'], 'pair_index': 0, 'arm': arm,
                                    'logodds_A_minus_B': 2. if x['label'] else -2.})
        result = aggregate(bank['rows'], records)
        swap = next(r for r in result['rows'] if r['row'] == row['key'])['paired_prompt_swap_control']
        self.assertEqual(swap['mean_correct_minus_wrong']['none'], -2.)
        self.assertEqual(swap['extra_model_calls'], 0)
        self.assertFalse(swap['used_in_R_b1_or_R_b2'])
        row['test'][0]['swap_donor_id'] = row['test'][0]['id']
        with self.assertRaises(ValueError):
            L.validate_labeled_bank(bank)
    def test_pooled_pca_fallback_exact_threshold(self):
        self.assertEqual(W.pca_population([{'dev': [None] * 767}]), 'pooled_dev_prompt_positions')
        self.assertEqual(W.pca_population([{'dev': [None] * 768}]), 'pooled_dev_read_points')
        self.assertEqual(len(L.validate_labeled_bank(bank_fixture())), 10)
        b = bank_fixture(5)
        self.assertEqual(b['pca_population'], 'pooled_dev_prompt_positions')
        L.validate_labeled_bank(b)

    def test_wrong_pca_control_pair_scope_and_label_rejected(self):
        for mutation in ('pca', 'shared_answer', 'reasoning_bridge', 'control_missing', 'test_omission', 'label'):
            b = bank_fixture()
            if mutation == 'pca': b['pca_population'] = 'row_own_PCA'
            if mutation == 'shared_answer': b['rows'][0]['test'][0]['pairs'][0]['B_ids'] = [4]
            if mutation == 'reasoning_bridge': b['rows'][0]['feature'] = 'reasoning_bridge'
            if mutation == 'control_missing': b['rows'][0]['control'] = False
            if mutation == 'test_omission': b['rows'][0]['test'].pop()
            if mutation == 'label': b['rows'][0]['test'][0]['label'] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                L.validate_labeled_bank(b)

    def test_custody_cap_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp); (path / 'POD_SOURCE_SEAL.20261027.json').write_text('{}')
            with patch.object(W, 'HERE', path):
                a = {'issuer': 'integrator', 'experiment': 'E58b', 'gpu_count': 1, 'pod_id': 'pod',
                     'request_sha256': 'a' * 64, 'input_seal_sha256': 'b' * 64,
                     'source_seal_sha256': W.sha(path / 'POD_SOURCE_SEAL.20261027.json'),
                     'source_pushed': True, 'external_hardstop_verified': True, 'hold_renewer_verified': True,
                     'budget_watch_verified': True, 'conditional_extension_authorized': True, 'prior_no_production_verified': True, 'retry_number': 1,
                     'source_commit': 'c' * 40, 'provider_created_epoch': 0, 'allocated_gpu_seconds': 2700,
                     'previous_gpu_seconds': 0, 'deadline_epoch': 2700, 'setup_deadline_epoch': 1500}
                self.assertEqual(W.assignment_check(a, 'a' * 64, 'b' * 64, now=100, pod_id='pod'), 2520)
                for key, value in [('allocated_gpu_seconds', 5401), ('previous_gpu_seconds', 3000),
                                   ('deadline_epoch', 2701), ('pod_id', 'other'),
                                   ('source_pushed', False), ('allocated_gpu_seconds', True)]:
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        W.assignment_check({**a, key: value}, 'a' * 64, 'b' * 64, now=100, pod_id='pod')

    def test_programme_stop_is_thursday_29_october(self):
        from datetime import datetime, timezone
        self.assertEqual(datetime.fromtimestamp(W.PROGRAMME_STOP, timezone.utc).isoformat(), '2026-10-29T22:59:00+00:00')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp); (path / 'POD_SOURCE_SEAL.20261027.json').write_text('{}')
            with patch.object(W, 'HERE', path):
                created = W.PROGRAMME_STOP - 2700
                a = {'issuer': 'integrator', 'experiment': 'E58b', 'gpu_count': 1, 'pod_id': 'pod',
                     'request_sha256': 'a' * 64, 'input_seal_sha256': 'b' * 64,
                     'source_seal_sha256': W.sha(path / 'POD_SOURCE_SEAL.20261027.json'),
                     'source_pushed': True, 'external_hardstop_verified': True, 'hold_renewer_verified': True,
                     'budget_watch_verified': True, 'conditional_extension_authorized': True, 'prior_no_production_verified': True, 'retry_number': 1,
                     'source_commit': 'c' * 40, 'provider_created_epoch': created, 'allocated_gpu_seconds': 2700,
                     'previous_gpu_seconds': 0, 'deadline_epoch': W.PROGRAMME_STOP, 'setup_deadline_epoch': created + 1500}
                self.assertEqual(W.assignment_check(a, 'a' * 64, 'b' * 64, now=created + 1, pod_id='pod'), W.PROGRAMME_STOP - 180)
                with self.assertRaises(ValueError):
                    W.assignment_check({**a, 'provider_created_epoch': created + 1, 'deadline_epoch': W.PROGRAMME_STOP + 1},
                                       'a' * 64, 'b' * 64, now=created + 2, pod_id='pod')


if __name__ == '__main__':
    unittest.main()
