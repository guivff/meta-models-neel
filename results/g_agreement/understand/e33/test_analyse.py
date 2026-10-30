"""Synthetic scientific contracts; no E33 model scores or test truth."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import numpy as np

from analyse import auc, compute, decide, validate_grid, join_collections, analyse, PREFIX, OPERATIONS
from prepare import HERE, read, dump, sha


def fixture(effect=False, full=False):
    plan = read(HERE / 'PLAN.json')
    templates = ({f: {'class': plan['classes'][f], 'values': ['a', 'b']} for f in plan['rows']} if full else
                 {'structure_test': {'class': 'state-like', 'values': ['a', 'b']},
                  'content_test': {'class': 'semantic', 'values': ['a', 'b']}})
    labels, scores, items = {}, [], []
    for feature in templates:
        for i in range(84):
            ident = feature + str(i)
            labels[ident] = {'feature': feature, 'value': 'a' if i % 2 else 'b', 'cluster': str(i // 14)}
            items.append({'id': ident, 'feature': feature})
            for prompt in plan['prompts']:
                for dose in plan['doses']:
                    score = float(i % 2)
                    if effect and templates[feature]['class'] != 'semantic':
                        score *= 1 - dose
                    scores.append({'id': ident, 'feature': feature, 'prompt': prompt, 'dose': dose,
                                   'scores': [score, score], 'score': score})
    return plan, templates, labels, scores, items


def jsonl(path, rows):
    path.write_text(''.join(json.dumps(r, sort_keys=True, allow_nan=False) + '\n' for r in rows))


def reseal(collection, status='E33_SHARD_COMPLETE'):
    dump(collection / 'SCORE_SEAL.json', {'status': status,
         'files': {p.name: sha(p) for p in collection.iterdir() if p.is_file() and p.name != 'SCORE_SEAL.json'}})


def joint_fixture(root, effect=True, pod_count=2):
    """Complete synthetic 25×84×2×5 sealed corpus with the runtime's v2 fields.

    All synthetic source/plan/input bytes live in an isolated temporary checkout.
    This helper never rewrites the registered production PLAN or existing input seal.
    """
    root = Path(root)
    here = root / 'repository' / PREFIX
    here.mkdir(parents=True)
    inputs = root / 'input'
    inputs.mkdir()
    plan, templates, labels, scores, items = fixture(effect=effect, full=True)
    label_path = root / 'SYNTHETIC_LABELS.jsonl'
    jsonl(label_path, [{'id': k, 'split': 'test', **v} for k, v in labels.items()])
    plan['private_labels_sha256'] = sha(label_path)
    dump(here / 'PLAN.json', plan)
    jsonl(inputs / 'items.input.jsonl', items)
    dump(inputs / 'templates.json', templates)
    dump(inputs / 'provenance.json', {'plan_sha256': sha(here / 'PLAN.json')})
    dump(inputs / 'INPUT_SEAL.json', {'files': {p.name: sha(p) for p in inputs.iterdir()}})
    operations = {'schema': 'E33_OPERATIONS_v2', 'previous_gpu_seconds': 407,
                  'global_cap_gpu_seconds': 16200, 'original_plan_sha256': sha(here / 'PLAN.json'),
                  'input_seal_sha256': sha(inputs / 'INPUT_SEAL.json')}
    dump(here / OPERATIONS, operations)
    for name in ('runtime.py', 'prepare.py', 'reused.py', 'analyse.py'):
        (here / name).write_text('# Synthetic frozen source identity for analysis tests only.\n')
    pins = {PREFIX + p.name: sha(p) for p in here.iterdir()}
    allocation = ([{'slot': 0, 'pod_id': 'synthetic0', 'doses': list(plan['doses']), 'allocated_gpu_seconds': 15793}]
                  if pod_count == 1 else
                  [{'slot': 0, 'pod_id': 'synthetic0', 'doses': plan['doses'][:3], 'allocated_gpu_seconds': 9475},
                   {'slot': 1, 'pod_id': 'synthetic1', 'doses': plan['doses'][3:], 'allocated_gpu_seconds': 6318}])
    run_plan = {'schema': 'E33_RUN_PLAN_v2', 'experiment': 'E33', 'run_id': 'synthetic-joint-run',
        'operations_sha256': sha(here / OPERATIONS), 'original_plan_sha256': sha(here / 'PLAN.json'),
        'input_seal_sha256': sha(inputs / 'INPUT_SEAL.json'), 'previous_gpu_seconds': 407,
        'global_cap_gpu_seconds': 16200, 'source_files': pins, 'allocations': allocation}
    collections = []
    for a in allocation:
        collection = root / ('pod' + str(a['slot']))
        collection.mkdir()
        dump(collection / 'run_plan.json', run_plan)
        jsonl(collection / 'scores.jsonl', [r for r in scores if r['dose'] in a['doses']])
        identity = {'run_id': run_plan['run_id'], 'run_plan_sha256': sha(collection / 'run_plan.json'),
            'operations_sha256': run_plan['operations_sha256'], 'original_plan_sha256': run_plan['original_plan_sha256'],
            'slot': a['slot'], 'pod_id': a['pod_id'], 'pod_count': pod_count, 'assigned_doses': a['doses'],
            'previous_gpu_seconds': 407, 'global_cap_gpu_seconds': 16200,
            'allocated_gpu_seconds': a['allocated_gpu_seconds'], 'expected_score_records': 4200 * len(a['doses']),
            'source_files': pins, 'input_seal_sha256': run_plan['input_seal_sha256'], 'status': 'COMPLETE',
            'activation_injection': False}
        dump(collection / 'provenance.json', identity)
        dump(collection / 'RUN.json', {**identity, 'provider_elapsed_seconds': 100,
            'budget_includes_setup': True, 'budget_clock_resets': 0, 'GPU_count': 1})
        reseal(collection)
        collections.append(collection)
    return {'here': here, 'inputs': inputs, 'collections': collections, 'labels': label_path,
            'plan': plan, 'run_plan': run_plan, 'items': items, 'scores': scores}


def change_provenance(collection, changes):
    for name in ('provenance.json', 'RUN.json'):
        p = read(collection / name)
        p.update(changes)
        dump(collection / name, p)
    reseal(collection)


class AnalysisTests(unittest.TestCase):
    def test_ties_and_orientation(self):
        self.assertEqual(auc([1, 1, 0, 0], [True, False, True, False]), .5)
        self.assertEqual(auc([1, 1, 0, 0], [True, True, False, False]), 1)
        self.assertEqual(auc([0, 0, 1, 1], [True, True, False, False]), 0)

    def test_paired_identical_dose_difference_exact_zero(self):
        plan, templates, labels, scores, _ = fixture()
        result = compute(scores, labels, templates, plan, n_boot=32)
        self.assertEqual(result['primary']['difference'], 0)
        self.assertEqual(result['primary']['ci95'], [0, 0])
        self.assertTrue(result['rules']['prompt_account'])
        self.assertFalse(result['rules']['adapter_policy'])

    def test_registered_policy_pattern_and_paired_ci(self):
        plan, templates, labels, scores, _ = fixture(effect=True)
        result = compute(scores, labels, templates, plan, n_boot=32)
        self.assertEqual(result['primary']['difference'], .5)
        self.assertEqual(result['primary']['ci95'], [.5, .5])
        self.assertTrue(result['rules']['adapter_policy'])
        self.assertFalse(result['rules']['prompt_account'])

    def test_noisy_identical_rankings_reuse_cluster_draws(self):
        plan, templates, labels, scores, _ = fixture()
        rng = np.random.default_rng(7)
        noisy = {key: float(rng.normal()) for key in labels}
        for r in scores:
            r['score'] = noisy[r['id']]
            r['scores'] = [r['score'], r['score']]
        result = compute(scores, labels, templates, plan, n_boot=32)
        self.assertEqual(result['primary']['ci95'], [0, 0])

    def test_boundary_ci_requires_strictly_positive(self):
        medians = {'structure': {'P1': [.90, .8, .7, .6, .60]}, 'semantic': {'P1': [.95] * 5}}
        self.assertFalse(decide(medians, .30, [0, .5])['adapter_policy'])
        self.assertTrue(decide(medians, .30, [.01, .5])['adapter_policy'])

    def test_grid_rejects_missing_duplicate_nonfinite_or_wrong_mean(self):
        plan, _, _, scores, items = fixture()
        validate_grid(scores, items, plan)
        bads = [scores[:-1], scores[:-1] + [scores[0]]]
        for change in [{'score': 99}, {'scores': [np.nan, 0]}, {'feature': 'other'}]:
            bad = copy.deepcopy(scores); bad[0].update(change); bads.append(bad)
        for bad in bads:
            with self.assertRaises(ValueError):
                validate_grid(bad, items, plan)

    def test_cluster_requires_paired_values(self):
        plan, templates, labels, scores, _ = fixture()
        for key in labels:
            labels[key]['cluster'] = labels[key]['value']
        with self.assertRaises(ValueError):
            compute(scores, labels, templates, plan, n_boot=4)


class ShardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='e33-synthetic-')
        self.root = Path(self.tmp.name)
        self.f = joint_fixture(self.root)
        self.here_patch = mock.patch('analyse.HERE', self.f['here'])
        self.here_patch.start()

    def tearDown(self):
        self.here_patch.stop()
        self.tmp.cleanup()

    def join(self, collections=None):
        return join_collections(self.f['inputs'], self.f['collections'] if collections is None else collections, self.f['plan'])

    def test_infrastructure_loss_stays_inside_slot_envelope_and_analysis_total(self):
        ledger = copy.deepcopy(self.f['run_plan'])
        slot = ledger['allocations'][0]
        slot.update(budget_envelope_gpu_seconds=slot['allocated_gpu_seconds'],
                    infrastructure_loss_gpu_seconds=600,
                    infrastructure_losses=[])
        slot['allocated_gpu_seconds'] -= 600
        receipt = {'schema': 'E33_INFRASTRUCTURE_LOSS_v1', 'issuer': 'integrator', 'experiment': 'E33',
                   'slot': 0, 'pod_id': 'stopped-fixture', 'status': 'EXITED', 'stopped': True,
                   'setup_only': True, 'science_gpu_seconds': 0, 'provider_gpu_seconds': 599.5,
                   'provider_stopped_epoch': 1000}
        for collection in self.f['collections']:
            dump(collection / 'infrastructure_loss_slot0_0.json', receipt)
        slot['infrastructure_losses'] = [{'pod_id': 'stopped-fixture',
            'receipt_path': '/remote/no-longer-available/receipt.json',
            'receipt_sha256': sha(self.f['collections'][0] / 'infrastructure_loss_slot0_0.json')}]
        for collection in self.f['collections']:
            dump(collection / 'run_plan.json', ledger)
            index = read(collection / 'provenance.json')['slot']
            change_provenance(collection, {'run_plan_sha256': sha(collection / 'run_plan.json'),
                                          'allocated_gpu_seconds': ledger['allocations'][index]['allocated_gpu_seconds']})
        _, _, lineage = self.join()
        self.assertEqual(lineage['reserved_total_gpu_seconds'], 16200)
        self.assertEqual(lineage['new_infrastructure_loss_gpu_seconds'], 600)
        self.assertEqual(lineage['prior_reserved_plus_worker_elapsed_seconds'], 1207)
        slot['allocated_gpu_seconds'] += 1
        for collection in self.f['collections']:
            dump(collection / 'run_plan.json', ledger)
            change_provenance(collection, {'run_plan_sha256': sha(collection / 'run_plan.json')})
        self.assert_rejected_before_labels()

    def assert_rejected_before_labels(self, collections=None):
        with self.assertRaises(ValueError):
            analyse(self.f['inputs'], self.f['collections'] if collections is None else collections,
                    self.root / 'PRIVATE_KEY_MUST_NOT_BE_OPENED', self.root / 'rejected-analysis')

    def test_complete_joint_grid_and_analysis(self):
        scores, items, lineage = self.join()
        self.assertEqual((len(scores), len(items)), (21000, 2100))
        self.assertEqual(lineage['collection_count'], 2)
        self.assertEqual(lineage['prior_reserved_plus_worker_elapsed_seconds'], 607)
        self.assertEqual(lineage['worker_observed_new_provider_seconds'], 200)
        self.assertEqual(lineage['reserved_total_gpu_seconds'], 16200)
        with mock.patch('analyse.compute', side_effect=lambda s, l, t, p: compute(s, l, t, p, n_boot=8)):
            rules = analyse(self.f['inputs'], list(reversed(self.f['collections'])), self.f['labels'], self.root / 'analysis')
        self.assertTrue(rules['adapter_policy'])
        self.assertFalse(rules['prompt_account'])
        self.assertTrue((self.root / 'analysis' / 'ANALYSIS_SEAL.json').is_file())

    def test_missing_duplicate_or_overlapping_shards_rejected(self):
        self.assert_rejected_before_labels(self.f['collections'][:1])
        self.assert_rejected_before_labels([self.f['collections'][0]] * 2)
        change_provenance(self.f['collections'][1], {'assigned_doses': [0.5, 0.75, 1]})
        self.assert_rejected_before_labels()

    def test_tampered_score_seal_rejected(self):
        path = self.f['collections'][0] / 'scores.jsonl'
        path.write_text(path.read_text() + '{}\n')
        self.assert_rejected_before_labels()

    def test_resealed_missing_score_and_duplicate_score_rejected(self):
        collection = self.f['collections'][0]
        path = collection / 'scores.jsonl'
        text = path.read_text().splitlines()
        path.write_text('\n'.join(text[:-1]) + '\n')
        reseal(collection)
        self.assert_rejected_before_labels()
        path.write_text('\n'.join(text[:-1] + [text[0]]) + '\n')
        reseal(collection)
        self.assert_rejected_before_labels()

    def test_mixed_sources_rejected(self):
        pins = dict(self.f['run_plan']['source_files'])
        pins[PREFIX + 'runtime.py'] = 'f' * 64
        change_provenance(self.f['collections'][1], {'source_files': pins})
        self.assert_rejected_before_labels()

    def test_local_frozen_source_tamper_rejected(self):
        (self.f['here'] / 'runtime.py').write_text('changed')
        self.assert_rejected_before_labels()

    def test_mixed_input_or_budget_rejected(self):
        collection = self.f['collections'][1]
        change_provenance(collection, {'input_seal_sha256': 'f' * 64})
        self.assert_rejected_before_labels()
        change_provenance(collection, {'input_seal_sha256': self.f['run_plan']['input_seal_sha256'],
                                       'previous_gpu_seconds': 0})
        self.assert_rejected_before_labels()

    def test_mixed_run_ledgers_rejected(self):
        collection = self.f['collections'][1]
        ledger = read(collection / 'run_plan.json')
        ledger['run_id'] = 'different-run'
        dump(collection / 'run_plan.json', ledger)
        change_provenance(collection, {'run_id': ledger['run_id'], 'run_plan_sha256': sha(collection / 'run_plan.json')})
        self.assert_rejected_before_labels()

    def test_prior_charge_cannot_reset_or_global_cap_expand(self):
        collection = self.f['collections'][0]
        ledger = read(collection / 'run_plan.json')
        ledger['previous_gpu_seconds'] = 0
        dump(collection / 'run_plan.json', ledger)
        change_provenance(collection, {'previous_gpu_seconds': 0, 'run_plan_sha256': sha(collection / 'run_plan.json')})
        self.assert_rejected_before_labels()
        ledger['previous_gpu_seconds'] = 407
        ledger['global_cap_gpu_seconds'] = 18000
        dump(collection / 'run_plan.json', ledger)
        change_provenance(collection, {'previous_gpu_seconds': 407, 'global_cap_gpu_seconds': 18000,
                                       'run_plan_sha256': sha(collection / 'run_plan.json')})
        self.assert_rejected_before_labels()

    def test_over_budget_provider_receipt_rejected(self):
        collection = self.f['collections'][0]
        receipt = read(collection / 'RUN.json')
        receipt['provider_elapsed_seconds'] = 9476
        dump(collection / 'RUN.json', receipt)
        reseal(collection)
        self.assert_rejected_before_labels()

    def test_no_fit_cannot_be_analysed(self):
        collection = self.f['collections'][0]
        change_provenance(collection, {'status': 'NO_FIT'})
        reseal(collection, status='E33_SHARD_NO_FIT')
        self.assert_rejected_before_labels()

    def test_required_scientific_file_cannot_be_unsealed(self):
        collection = self.f['collections'][0]
        seal = read(collection / 'SCORE_SEAL.json')
        del seal['files']['scores.jsonl']
        dump(collection / 'SCORE_SEAL.json', seal)
        self.assert_rejected_before_labels()

    def test_one_pod_new_and_legacy_full_grid_supported(self):
        with tempfile.TemporaryDirectory(prefix='e33-one-pod-') as d:
            f = joint_fixture(Path(d), pod_count=1)
            with mock.patch('analyse.HERE', f['here']):
                scores, _, lineage = join_collections(f['inputs'], f['collections'], f['plan'])
                self.assertEqual(len(scores), 21000)
                self.assertFalse(lineage['legacy_single_full_grid'])
                reseal(f['collections'][0], status='E33_COMPLETE')
                _, _, lineage = join_collections(f['inputs'], f['collections'][0], f['plan'])
                self.assertTrue(lineage['legacy_single_full_grid'])

    def test_legacy_shard_does_not_bypass_complete_grid(self):
        collection = self.f['collections'][0]
        reseal(collection, status='E33_COMPLETE')
        self.assert_rejected_before_labels([collection])


if __name__ == '__main__':
    unittest.main()
