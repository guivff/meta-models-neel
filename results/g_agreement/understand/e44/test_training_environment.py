"""CPU contracts for immutable environment, parity, and readiness boundaries."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import training_environment as E
import worker as W


def snapshots():
    before = {'python_version': 'fixture', 'executable_sha256': 'a'*64, 'prefix': '/base',
              'modules': {n: {'tree_sha256': n} for n in E.INHERITED}}
    before['modules']['triton'] = None
    after = copy.deepcopy(before)
    after['prefix'] = '/tmp/e44-fixture'
    after['modules']['triton'] = {'distributions': [{'version': '3.7.1'}]}
    return before, after


class EnvironmentContracts(unittest.TestCase):
    def test_only_approved_triton_change(self):
        before, after = snapshots()
        E.validate_preserved(before, after)
        after['modules']['torch']['tree_sha256'] = 'tampered'
        with self.assertRaises(E.EnvironmentNotReady):
            E.validate_preserved(before, after)

    def test_hopper_incompatible_version_rejected(self):
        before, after = snapshots()
        after['modules']['triton']['distributions'][0]['version'] = '3.4.0'
        with self.assertRaises(E.EnvironmentNotReady):
            E.validate_preserved(before, after)

    def test_prepared_is_not_ready_and_live_state_is_bound(self):
        before, after = snapshots()
        value = {'schema': 'E44_TRAINING_ENVIRONMENT_v1', 'status': 'PREPARED_FROZEN',
            'readiness_deadline_epoch': E.READINESS_DEADLINE, 'prepared_epoch': 100,
            'cuda_backward_verified': False, 'model_forwards': 0, 'optimizer_steps': 0,
            'base_snapshot': before, 'overlay_snapshot': after}
        E.validate_prepared(value, after, 101)
        with self.assertRaises(E.EnvironmentNotReady):
            E.validate_prepared(value, after, E.READINESS_DEADLINE+1)
        altered = copy.deepcopy(after)
        altered['modules']['peft']['tree_sha256'] = 'modified'
        with self.assertRaises(E.EnvironmentNotReady):
            E.validate_prepared(value, altered, 101)
        value['cuda_backward_verified'] = True
        with self.assertRaises(E.EnvironmentNotReady):
            E.validate_prepared(value, after, 101)

    def test_cpu_or_late_backward_cannot_certify_cuda(self):
        diagnostics = {'finite_loss': True, 'finite_gradients': True, 'frozen_parameter_grads_none': True}
        for device, epoch in [('cpu', 100), ('cuda', E.READINESS_DEADLINE+1), ('cuda', float('nan'))]:
            with self.assertRaises(E.EnvironmentNotReady):
                E.runtime_ready(diagnostics, device, epoch, 'env', 'parity')
        result = E.runtime_ready(diagnostics, 'cuda:0', 100, 'env', 'parity')
        self.assertTrue(result['cuda_backward_verified'])
        self.assertEqual(result['optimizer_steps_in_readiness'], 1)
        diagnostics['finite_gradients'] = False
        with self.assertRaises(E.EnvironmentNotReady):
            E.runtime_ready(diagnostics, 'cuda', 100, 'env', 'parity')

    def test_package_roots_keep_global_dist_packages_order(self):
        with tempfile.TemporaryDirectory() as root:
            a, b = Path(root)/'base/site-packages', Path(root)/'system/dist-packages'
            a.mkdir(parents=True); b.mkdir(parents=True)
            with mock.patch.object(sys, 'path', [root, str(a), str(b), str(a)]):
                self.assertEqual(E.package_paths(), [str(a.resolve()), str(b.resolve())])

    def test_wheel_hash_pins_only_required_dependency(self):
        text = (E.HERE / 'OVERLAY_REQUIREMENTS.txt').read_text()
        lines = [x.strip() for x in text.splitlines() if x.strip() and not x.startswith('#')]
        self.assertEqual(lines[0], 'triton==3.7.1 \\')
        self.assertEqual(len(lines)-1, 5)
        self.assertTrue(all(x.startswith('--hash=sha256:') for x in lines[1:]))

    def test_tree_byte_changes_detected_bytecode_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root); (p/'module.py').write_text('a')
            first = E.tree_manifest(p)['tree_sha256']
            (p/'__pycache__').mkdir(); (p/'__pycache__/module.pyc').write_bytes(b'x')
            self.assertEqual(first, E.tree_manifest(p)['tree_sha256'])
            (p/'module.py').write_text('b')
            self.assertNotEqual(first, E.tree_manifest(p)['tree_sha256'])

    def test_run_parity_failure_cannot_create_optimizer(self):
        from types import SimpleNamespace
        import time
        import torch
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base/'cache').mkdir()
            environment = base/'environment.json'
            W.C.dump(environment, {})
            args = SimpleNamespace(assignment=base/'assignment.json', out=base/'cache/run',
                                   environment_manifest=environment, parity_inputs=base/'gate', release_gate=W.C.HERE/'E39_RELEASE_GATE_2026-10-26.json')
            assignment = {'provider_created_epoch': time.time(), 'deadline_epoch': time.time()+600,
                          'training_environment_sha256': W.C.sha(environment),
                          'parity_input_seal_sha256': 'p', 'runs': [], 'previous_gpu_seconds': 0,
                          'release_gate_sha256':W.C.sha(args.release_gate)}
            W.C.dump(args.assignment, assignment)
            inputs = (assignment, {}, {}, [], [], [], [], {})
            with mock.patch.object(W.C, 'assignment', side_effect=lambda x:x), \
                 mock.patch.object(W,'check_source'), mock.patch.object(W.E, 'verify_manifest'), mock.patch.object(W, 'runtime_inputs', return_value=inputs), \
                 mock.patch.object(W, 'parity_inputs'), mock.patch.object(W, 'load_base', return_value=(torch.nn.Linear(2,2), None)), \
                 mock.patch.object(W, 'make_reader'), mock.patch.object(W, 'arm_deadline'), \
                 mock.patch.object(W, 'parity_gate', side_effect=W.ParityFailed), \
                 mock.patch.object(W, 'attach_lowrank', side_effect=AssertionError('adapter before parity')), \
                 mock.patch.object(W, 'optimizer_for', side_effect=AssertionError('optimizer before parity')), \
                 mock.patch.object(W, 'train_step', side_effect=AssertionError('step before parity')):
                with self.assertRaises(W.ParityFailed):
                    W.run(args)
            receipt = W.C.read(args.out/'RUN_RECEIPT.json')
            self.assertEqual(receipt['status'], 'PARITY_FAILED_STOP')
            self.assertFalse(receipt['retry_authorized'])

    def test_parity_pass_and_fail_before_optimizer(self):
        from types import SimpleNamespace
        import torch
        import numpy as np
        items = [{'id': f'{row}-{i}', 'feature': row} for row in W.PARITY_ROWS for i in range(84)]
        labels = {item['id']: i % 2 for i, item in enumerate(items)}
        refs = {'reference_auc': {row: 1.0 for row in W.PARITY_ROWS}}
        model = torch.nn.Linear(2, 2)
        for parameter in model.parameters(): parameter.requires_grad_(False)
        reader = SimpleNamespace(model=model)
        inputs = (items, labels, {row: {} for row in W.PARITY_ROWS}, np.zeros((252,2)), refs)
        def scoring(_reader, records, _acts, _spec, row):
            return [{'id': r['id'], 'scores': [float(labels[r['id']])]*2} for r in records if r['feature']==row]
        with tempfile.TemporaryDirectory() as root:
            source, out = Path(root)/'source', Path(root)/'out'
            source.mkdir(); out.mkdir(); W.C.dump(source/'REFERENCE.json', refs)
            with mock.patch.object(W, 'score', side_effect=scoring), mock.patch.object(W, 'optimizer_for', side_effect=AssertionError):
                result = W.parity_gate(reader, inputs, source, out, {'parity_input_seal_sha256':'s'}, 'e')
                self.assertEqual(result['status'], 'PASS')
                self.assertEqual(result['optimizer_steps_before_gate'], 0)
                self.assertEqual(len(W.C.rows(out/'PARITY_SCORES.jsonl')), 252)
                refs['reference_auc']['prose_sentiment'] = .5
                with self.assertRaises(W.ParityFailed):
                    W.parity_gate(reader, inputs, source, out, {'parity_input_seal_sha256':'s'}, 'e')
                self.assertEqual(W.C.read(out/'PARITY_RESULT.json')['status'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
