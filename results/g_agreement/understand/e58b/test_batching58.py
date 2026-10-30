"""CPU checks of full-token prefix scoring, batching, memory and cap admission."""
import unittest
import numpy as np
import torch
from batching58 import prefix_plan, batches, accumulate, finish, choose_budget
from projection58 import projection_hook
from worker58 import Backend, memory_safe
from test58 import ToyModel


class PrefixTests(unittest.TestCase):
    def test_shared_prefixes_keep_every_candidate_token(self):
        item = {'id': 'item', 'ids': [1, 2], 'pairs': [
            {'A_ids': [3, 4, 5], 'B_ids': [3, 4, 6]}, {'A_ids': [3], 'B_ids': [7]}]}
        nodes, candidates = prefix_plan([{'key': 'row', 'test': [item]}])
        self.assertEqual(len(nodes), 3)
        terms = {key: [None] * n for key, n in candidates.items()}
        accumulate(terms, nodes, [{t: -float(t) for t in n['targets']} for n in nodes])
        values = finish(terms)
        self.assertEqual(values['row', 'item', 0, 'A'], -12.)
        self.assertEqual(values['row', 'item', 0, 'B'], -13.)
        self.assertEqual(values['row', 'item', 1, 'A'], -3.)
        self.assertEqual(values['row', 'item', 1, 'B'], -7.)

    def test_global_large_batches_are_exhaustive(self):
        values = list(range(141))
        for size in (32, 64):
            chunks = batches(values, size)
            self.assertEqual([x for c in chunks for x in c], values)
            self.assertTrue(all(0 < len(c) <= size for c in chunks))

    def test_left_padding_projection_excludes_padding_and_candidate_prefix(self):
        h = torch.arange(40).reshape(2, 5, 4).float()
        q = torch.eye(4)[:, :2]
        actual = projection_hook(q, [2, 3], [2, 0])(None, None, h)
        self.assertTrue(torch.equal(actual[0, :2], h[0, :2]))
        self.assertTrue(torch.equal(actual[0, 4:], h[0, 4:]))
        self.assertTrue(torch.equal(actual[1, 3:], h[1, 3:]))
        self.assertEqual(float(actual[0, 2:4, :2].abs().sum()), 0.)

    def test_prefix_scoring_matches_full_teacher_forcing_under_projection(self):
        backend = Backend.__new__(Backend); backend.model = ToyModel(); backend.layer = backend.model.layer; backend.device = 'cpu'
        items = [{'id': 'a', 'ids': [1, 2], 'pairs': [{'A_ids': [3, 4, 5], 'B_ids': [3, 4, 6]}]},
                 {'id': 'b', 'ids': [2], 'pairs': [{'A_ids': [4], 'B_ids': [5, 6]}]}]
        for q in (None, torch.eye(4)[:, :2]):
            actual = backend.score([(x, 0) for x in items], q)
            expected = []
            for x in items:
                values = []
                for side in ('A_ids', 'B_ids'):
                    candidate = x['pairs'][0][side]; ids = torch.tensor([x['ids'] + candidate]); mask = torch.ones_like(ids)
                    handle = backend.layer.register_forward_hook(projection_hook(q, [len(x['ids'])])) if q is not None else None
                    try:
                        output = backend.model(ids, mask, torch.arange(ids.shape[1]), False).logits[0].float().log_softmax(-1)
                        positions = torch.arange(len(x['ids']) - 1, len(x['ids']) - 1 + len(candidate))
                        values.append(float(output[positions, torch.tensor(candidate)].sum().detach()))
                    finally:
                        if handle: handle.remove()
                expected.append(tuple(values))
            np.testing.assert_allclose(actual, expected, atol=1e-6)
        self.assertEqual(len(backend.layer._forward_hooks), 0)

    def test_missing_and_duplicate_token_probabilities_stop(self):
        item = {'id': 'i', 'ids': [1], 'pairs': [{'A_ids': [2], 'B_ids': [3]}]}
        nodes, candidates = prefix_plan([{'key': 'r', 'test': [item]}]); terms = {k: [None] * n for k, n in candidates.items()}
        with self.assertRaises(ValueError): finish(terms)
        values = [{t: -1. for t in n['targets']} for n in nodes]
        accumulate(terms, nodes, values)
        with self.assertRaises(ValueError): accumulate(terms, nodes, values)


class AdmissionTests(unittest.TestCase):
    def test_preferred_cap_kept_when_full_run_fits(self):
        a = {'provider_created_epoch': 100., 'previous_gpu_seconds': 400., 'deadline_epoch': 5100.}
        b = choose_budget(a, 900., 300.)
        self.assertEqual(b['selected_total_gpu_seconds'], 2700)
        self.assertFalse(b['extension_used'])
        self.assertEqual(b['effective_provider_deadline_epoch'], 2400.)

    def test_extension_only_after_preferred_does_not_fit(self):
        a = {'provider_created_epoch': 100., 'previous_gpu_seconds': 400., 'deadline_epoch': 5100.}
        b = choose_budget(a, 1600., 300.)
        self.assertEqual(b['selected_total_gpu_seconds'], 5400)
        self.assertTrue(b['extension_used']); self.assertFalse(b['preferred_fit'])
        self.assertEqual(choose_budget(a, 4000., 300.)['status'], 'NO_FIT')

    def test_no_extension_beyond_assigned_deadline(self):
        a = {'provider_created_epoch': 100., 'previous_gpu_seconds': 400., 'deadline_epoch': 2400.}
        self.assertEqual(choose_budget(a, 1600., 300.)['status'], 'NO_FIT')

    def test_memory_margin(self):
        gb = 1024 ** 3
        self.assertTrue(memory_safe(140 * gb, 30 * gb, 100 * gb))
        self.assertFalse(memory_safe(140 * gb, 3 * gb, 100 * gb))
        self.assertFalse(memory_safe(140 * gb, 30 * gb, 139 * gb))


if __name__ == '__main__':
    unittest.main()
