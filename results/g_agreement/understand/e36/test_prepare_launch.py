"""CPU-only guards for integrator binding; no real bank or asset inventory."""
import unittest
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import channel_contract as C
import prepare_launch as P
import worker as W
import parity_gate as G


def synthetic_request():
    x = {'schema': 'e36.source-ready.v1', 'status': 'READY_FOR_INTEGRATOR_BINDING',
         'operator': 'integrator', 'bank_frozen': True, 'model_calls': 0,
         'scope_id': 'expanded25',
         'parity_inputs': {'path': 'INPUT_SEAL.json', 'sha256': G.INPUT_SHA256},
         'bindings': {key: {'path': 'synthetic', 'sha256': 'a'*64}
                      for key in ('bank', 'freeze', 'candidates')}}
    x['request_sha256'] = C.canonical_hash(x)
    return x


class ReadyTests(unittest.TestCase):
    def test_ready_request_integrity(self):
        x = synthetic_request()
        self.assertEqual(P.validate_ready_request(x), x['bindings'])
        x['bindings']['bank']['sha256'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            P.validate_ready_request(x)

    def test_hold_cannot_be_bound(self):
        x = synthetic_request()
        x['status'] = 'HOLD'
        del x['request_sha256']
        x['request_sha256'] = C.canonical_hash(x)
        with self.assertRaisesRegex(ValueError, 'held or incomplete'):
            P.validate_ready_request(x)

    def test_unfrozen_request_cannot_be_bound(self):
        x = synthetic_request()
        x['bank_frozen'] = False
        del x['request_sha256']
        x['request_sha256'] = C.canonical_hash(x)
        with self.assertRaisesRegex(ValueError, 'must be frozen'):
            P.validate_ready_request(x)

    def test_worker_resolves_bindings_from_assigned_checkout(self):
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo = base / 'checkout'
            repo.mkdir()
            for name in ('plan', 'assignment'):
                (base / (name + '.json')).write_text('{}')
            calls = []
            def run(plan, assignment, root, assets, out):
                self.assertEqual(Path.cwd(), repo.resolve())
                self.assertEqual(root, repo.resolve())
                self.assertEqual(assets, (base / 'assets.json').resolve())
                self.assertEqual(out, (base / 'run').resolve())
                calls.append(True)
            try:
                os.chdir(base)
                with patch.object(W, 'run_worker', run), patch.object(sys, 'path', list(sys.path)):
                    W.main(['--root', 'checkout', '--plan', 'plan.json', '--assignment', 'assignment.json',
                            '--assets', 'assets.json', '--out', 'run'])
            finally:
                os.chdir(original_cwd)
            self.assertEqual(calls, [True])


if __name__ == '__main__':
    unittest.main()
