"""E37 synthetic analysis contracts; no real test truth, model calls, or GPU."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

_spec = importlib.util.spec_from_file_location('e37_analysis_under_test', Path(__file__).with_name('analyse.py'))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

EXPLICIT = {
    'json_type': ('string value', 'numeric value'),
    'latex_environment': ('equation environment', 'quote environment'),
    'latex_section': ('early section', 'later section'),
    'list_depth': ('shallow list item', 'deep list item'),
    'list_index': ('first list item', 'later list item'),
    'prose_paren': ('inside a parenthesis', 'outside any parentheses'),
    'prose_quote': ('open quotation', 'closed quotation'),
    'prose_sentence': ('early sentence in a paragraph', 'later sentence in a paragraph'),
    'python_argument': ('first argument', 'later argument'),
    'python_comment': ('python comment', 'executable python code'),
    'python_depth': ('shallow nesting', 'deep nesting'),
    'python_indent': ('one level of indentation', 'three levels of indentation'),
    'python_string': ('open string literal', 'closed string literal'),
    'table_column': ('first table column', 'later table column'),
    'table_role': ('table header cell', 'table data cell'),
    'table_row': ('early table data row', 'later table data row'),
}


def fixture():
    frozen = A.read(A.HERE.parent / 'e33' / 'PLAN.json')
    plan = {'experiment': 'E37', 'rows': frozen['rows'], 'classes': frozen['classes'],
            'values': {f: ['a', 'b'] for f in frozen['rows']}, 'c2_rows': list(A.C2_ROWS),
            'bootstrap': {'seed': 20261025, 'n_boot': 2000}, 'r4_scope': 'pooled'}
    templates = {c: {f: [['- A', '- B'], ['- A again', '- B again']]
                    for f in (A.C2_ROWS if c == 'C2' else plan['rows'])} for c in A.CHANNELS}
    items, scores, free, labels = [], [], [], {}
    for feature in plan['rows']:
        for i in range(84):
            ident = feature + '-' + str(i).zfill(3)
            donor = feature + '-' + str(i ^ 1).zfill(3)
            items.append({'id': ident, 'feature': feature, 'donor_id': donor})
            labels[ident] = {'id': ident, 'feature': feature, 'split': 'test',
                             'value': 'a' if i % 2 else 'b', 'cluster': str(i // 14)}
            for arm in A.ARMS:
                free.append({'id': ident, 'feature': feature, 'arm': arm, 'raw': 'No explicit state statement.'})
                for channel in A.CHANNELS:
                    if feature not in templates[channel]:
                        continue
                    for control in (('matched', 'opposite') if channel == 'C2' else ('matched',)):
                        value = float(i % 2) * (1 if control == 'matched' else -1)
                        row = {'id': ident, 'feature': feature, 'arm': arm, 'channel': channel,
                               'control': control, 'scores': [value, value], 'score': value}
                        if control == 'opposite':
                            row['donor_id'] = donor
                        scores.append(row)
    return plan, templates, items, labels, scores, free


def jsonl(path, rows):
    path.write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))


def seal(directory, name, status=None):
    obj = {'files': {p.name: A.sha(p) for p in directory.iterdir() if p.is_file() and p.name != name}}
    if status:
        obj['status'] = status
    A.dump(directory / name, obj)


def sealed_fixture(root):
    root = Path(root)
    here = root / 'repository' / A.PREFIX
    here.mkdir(parents=True)
    inputs, collection = root / 'inputs', root / 'collection'
    inputs.mkdir()
    collection.mkdir()
    plan, templates, items, labels, scores, free = fixture()
    labels_path = root / 'SYNTHETIC_LABELS.jsonl'
    jsonl(labels_path, list(labels.values()))
    plan['private_labels_sha256'] = A.sha(labels_path)
    A.dump(here / 'PLAN.json', plan)
    for name in ('checkpoint_cpu.py', 'CHECKPOINT_MANIFEST_2026-10-26.json'):
        (here / name).write_bytes((A.HERE / name).read_bytes())
    for name in ('runtime.py', 'analyse.py'):
        (here / name).write_text('# Synthetic source identity for CPU tests only.\n')
    A.dump(here / 'PARITY_GATE.json', {'status': 'REGISTERED_FROZEN', 'synthetic_test_only': True})
    relative_regex = 'projects/g_agreement/understand/e24_statements.py'
    regex = here.parents[3] / relative_regex
    regex.parent.mkdir(parents=True)
    regex.write_bytes((A.ROOT / relative_regex).read_bytes())
    pins = {A.PREFIX + name: A.sha(here / name) for name in ('PLAN.json', 'runtime.py', 'analyse.py', 'PARITY_GATE.json', 'checkpoint_cpu.py', 'CHECKPOINT_MANIFEST_2026-10-26.json')}
    pins[relative_regex] = A.sha(regex)
    jsonl(inputs / 'items.input.jsonl', items)
    A.dump(inputs / 'templates.json', templates)
    A.dump(inputs / 'provenance.json', {'plan_sha256': A.sha(here / 'PLAN.json')})
    A.dump(inputs / 'parity_inputs.json', {'rl_reference_auc': {f: .8 for f in ('prose_sentiment', 'prose_paren', 'python_string')}})
    seal(inputs, 'INPUT_SEAL.json')
    jsonl(collection / 'scores.jsonl', scores)
    jsonl(collection / 'free.jsonl', free)
    provenance = {'status': 'COMPLETE', 'plan_sha256': A.sha(here / 'PLAN.json'),
                  'input_seal_sha256': A.sha(inputs / 'INPUT_SEAL.json'), 'source_files': pins}
    checkpoint = {'schema': 'E37_SFT_RECEIPT_v1', 'status': 'RECEIVED_FROZEN', 'issuer': 'integrator',
                  'provided_by': 'Agam', 'checkpoint_identity': 's3d.omp4bp.s2/step251',
                  'identity_verified': True, 'frozen_before_model_calls': True, 'model_calls_before_freeze': 0,
                  'received_epoch': A.CHECKPOINT_ARRIVAL_DEADLINE - 3600,
                  'files': {'adapter_config.json': 'a'*64, 'adapter_model.safetensors': 'b'*64}}
    from test_checkpoint_cpu import unverified_fixture
    cpu=unverified_fixture();cpu['received_epoch']=checkpoint['received_epoch']
    A.dump(collection / 'CPU_TENSOR_CHECK.json',cpu)
    checkpoint.update(files=cpu['selected_files'],selected_branch=cpu['selected_branch'],
                      cpu_tensor_check_sha256=A.sha(collection / 'CPU_TENSOR_CHECK.json'))
    provenance.update(cpu_tensor_check_sha256=A.sha(collection / 'CPU_TENSOR_CHECK.json'),
                      selected_branch=cpu['selected_branch'],readme_identity_claim_verified=False)
    gates = {'checkpoint_receipt.json': checkpoint,
             'parity_gate.json': A.read(here / 'PARITY_GATE.json'),
             'PARITY_RESULT.json': {'status': 'PASS', 'synthetic_test_only': True,
                'gate_order':'RL_three_row_reproduction_then_RL_smoke_then_SFT_smoke',
                'smoke': {a: {'items': 20, 'finite': True, 'threshold': 1e-4, 'max_abs_self_repeat_delta': 0} for a in A.ARMS},
                'RL_row_auroc': {f: {'n': 84, 'observed': .8, 'W1_reference': .8, 'absolute_delta': 0, 'threshold': .03}
                                 for f in ('prose_sentiment', 'prose_paren', 'python_string')}},
             'predecessors.json': {'schema': 'E37_PREREQUISITE_COMPLETION_v1', 'issuer': 'integrator', 'status': 'COMPLETE',
                'experiments': {e: {'status': 'COMPLETE', 'receipts': [{'path': 'synthetic-only', 'sha256': 'c'*64}]}
                                for e in ('E33', 'E28')}}}
    fields = ('checkpoint_receipt_sha256', 'parity_gate_sha256', 'parity_result_sha256', 'predecessors_sha256')
    for (name, value), field in zip(gates.items(), fields):
        A.dump(collection / name, value)
        provenance[field] = A.sha(collection / name)
    A.dump(collection / 'provenance.json', provenance)
    A.dump(collection / 'RUN.json', {**provenance, 'experiment': 'E37', 'provider_elapsed_seconds_at_worker_exit': 100,
        'allocated_gpu_seconds': 5400, 'budget_includes_setup': True, 'budget_clock_resets': 0, 'GPU_count': 1})
    seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
    return {'here': here, 'inputs': inputs, 'collection': collection, 'labels': labels_path,
            'plan': plan, 'templates': templates, 'items': items, 'scores': scores, 'free': free}


class StatisticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = fixture()

    def compute(self, scores=None, free=None, plan=None):
        p, t, _, labels, s, f = self.f
        return A.compute(s if scores is None else scores, f if free is None else free,
                         labels, t, p if plan is None else plan, n_boot=16)

    def test_complete_fixed_grid(self):
        p, t, items, _, scores, free = self.f
        self.assertEqual((len(scores), len(free)), (10752, 4200))
        A.validate_grid(scores, free, items, t, p)

    def test_all_registered_predictions_on_identical_arms(self):
        result = self.compute()
        self.assertTrue(result['rules']['R1']['met'])
        self.assertTrue(result['rules']['R2']['met'])
        self.assertTrue(result['rules']['R4']['met'])
        self.assertEqual(result['rules']['R4']['pooled']['arms']['RL']['n'], 1344)
        self.assertEqual(result['rules']['R4']['pooled']['arms']['SFT']['n'], 1344)
        self.assertTrue(all(r['difference_ci95'] == [0, 0] for r in result['paired_rows']))
        opposite = [r for r in result['paired_rows'] if r['control'] == 'opposite']
        self.assertEqual(len(opposite), 7)
        self.assertTrue(all(r['arms']['RL']['auroc'] == 0 for r in opposite))

    def test_pooled_r4_does_not_require_every_row_upper_below_five_percent(self):
        free = copy.deepcopy(self.f[-1])
        for row in free:
            if row['feature'] in EXPLICIT and row['id'].endswith('-000'):
                row['raw'] = EXPLICIT[row['feature']][1]
        result = self.compute(free=free)
        rule = result['rules']['R4']
        self.assertTrue(rule['met'])
        self.assertTrue(rule['pooled']['met'])
        self.assertFalse(rule['all_rows']['met'])
        self.assertEqual(rule['pooled']['arms']['RL']['correct'], 16)

    def test_both_and_neither_are_not_correct_statements(self):
        free = copy.deepcopy(self.f[-1])
        for row in free:
            if row['feature'] in EXPLICIT:
                row['raw'] = '\n'.join(EXPLICIT[row['feature']])
        result = self.compute(free=free)
        self.assertEqual(result['rules']['R4']['pooled']['arms']['RL']['correct'], 0)
        self.assertEqual(result['rules']['R4']['pooled']['arms']['SFT']['correct'], 0)

    def test_semantic_absent_regex_is_retained_not_evaluable(self):
        result = self.compute()
        semantic = [r for r in result['naming_rows'] if r['class'] == 'semantic']
        self.assertEqual(len(semantic), 9)
        self.assertTrue(all(r['status'] == 'NOT_EVALUABLE_NO_FROZEN_REGEX' for r in semantic))
        self.assertTrue(all(r['arms']['SFT'] is None for r in semantic))

    def test_r2_row_difference_can_fail_while_class_median_matches(self):
        scores = copy.deepcopy(self.f[-2])
        for row in scores:
            if row['feature'] == 'prose_paren' and row['channel'] == 'C1' and row['arm'] == 'SFT':
                row['score'] = -row['score']
                row['scores'] = [row['score']] * 2
        result = self.compute(scores=scores)
        self.assertEqual(result['rules']['R2']['structure_median_SFT_minus_RL'], 0)
        self.assertFalse(result['rules']['R2']['met'])
        self.assertEqual(result['rules']['R2']['large_significant_structure_rows'], ['prose_paren'])

    def test_r1_requires_five_qualified_rows(self):
        scores = copy.deepcopy(self.f[-2])
        for row in scores:
            if row['feature'] in A.C2_ROWS[:3] and row['channel'] == 'C2' and row['control'] == 'matched' and row['arm'] == 'SFT':
                row['score'] = -row['score']
                row['scores'] = [row['score']] * 2
        result = self.compute(scores=scores)
        self.assertFalse(result['rules']['R1']['met'])
        self.assertEqual(len(result['rules']['R1']['qualifying_rows']), 4)

    def test_r3_reverses_difference_and_interval_for_description(self):
        scores = copy.deepcopy(self.f[-2])
        for row in scores:
            if row['feature'] == 'prose_sentiment' and row['channel'] == 'C1' and row['arm'] == 'SFT':
                row['score'] = -row['score']
                row['scores'] = [row['score']] * 2
        result = self.compute(scores=scores)
        row = next(r for r in result['rules']['R3']['content_RL_minus_SFT'] if r['feature'] == 'prose_sentiment')
        self.assertEqual(row['RL_minus_SFT'], 1)
        self.assertEqual(row['difference_ci95'], [1, 1])
        self.assertEqual(result['rules']['R3']['status'], 'DESCRIPTIVE')

    def test_pairing_cancels_identical_noisy_arm_scores(self):
        scores = copy.deepcopy(self.f[-2])
        rng = np.random.default_rng(4)
        noisy = {r['id']: float(rng.normal()) for r in self.f[2]}
        for row in scores:
            row['score'] = noisy[row['id']]
            row['scores'] = [row['score']] * 2
        result = self.compute(scores=scores)
        self.assertTrue(all(r['difference_ci95'] == [0, 0] for r in result['paired_rows']))

    def test_registered_r1_r2_boundaries(self):
        plan = self.f[0]
        rows = [{'feature': f, 'class': 'state-like', 'channel': 'C2', 'control': 'matched',
                 'SFT_minus_RL': .05, 'arms': {'RL': {'auroc': .65}, 'SFT': {'auroc': .70}},
                 'difference_ci95': [-.1, .1]} for f in A.C2_ROWS]
        rows.append({'feature': 'prose_paren', 'class': 'state-like', 'channel': 'C1', 'control': 'matched',
                     'SFT_minus_RL': .15, 'difference_ci95': [0, .2]})
        medians = {'structure': {'SFT_minus_RL': .05}}
        result = A.finish_rules(rows, [], {}, medians, plan, 8)
        self.assertTrue(result['rules']['R1']['met'])
        self.assertTrue(result['rules']['R2']['met'])
        rows[-1]['difference_ci95'] = [.001, .2]
        self.assertFalse(A.finish_rules(rows, [], {}, medians, plan, 8)['rules']['R2']['met'])
        rows[-1]['difference_ci95'] = [0, .2]
        medians['structure']['SFT_minus_RL'] = .050001
        self.assertFalse(A.finish_rules(rows, [], {}, medians, plan, 8)['rules']['R2']['met'])


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='e37-analysis-synthetic-')
        self.root = Path(self.tmp.name)
        self.f = sealed_fixture(self.root)
        self.patch = mock.patch.object(A, 'HERE', self.f['here'])
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def reject_before_labels(self):
        with self.assertRaises(ValueError):
            A.analyse(self.f['inputs'], self.f['collection'], self.root / 'MUST_NOT_OPEN_PRIVATE_TRUTH', self.root / 'out')

    def test_full_synthetic_pipeline(self):
        original = A.compute
        with mock.patch.object(A, 'compute', side_effect=lambda *args: original(*args, n_boot=8)):
            rules = A.analyse(self.f['inputs'], self.f['collection'], self.f['labels'], self.root / 'out')
        self.assertTrue(rules['R1']['met'] and rules['R2']['met'] and rules['R4']['met'])
        self.assertTrue((self.root / 'out' / 'RESULTS.md').exists())

    def test_explicit_predecessor_closure_satisfies_queue_priority(self):
        collection = self.f['collection']
        data = A.read(collection / 'predecessors.json')
        data['status'] = 'READY_AFTER_PREDECESSORS'
        data['experiments']['E28']['status'] = 'NOT_RUN'
        A.dump(collection / 'predecessors.json', data)
        provenance = A.read(collection / 'provenance.json')
        provenance['predecessors_sha256'] = A.sha(collection / 'predecessors.json')
        A.dump(collection / 'provenance.json', provenance)
        seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
        A.validate_collection(self.f['inputs'], collection, self.f['plan'])

    def test_missing_duplicate_and_foreign_score_grid_rejected(self):
        collection = self.f['collection']
        scores = self.f['scores']
        for replacement in (scores[:-1], scores[:-1] + [scores[0]]):
            jsonl(collection / 'scores.jsonl', replacement)
            seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
            self.reject_before_labels()

    def test_missing_free_text_rejected(self):
        jsonl(self.f['collection'] / 'free.jsonl', self.f['free'][:-1])
        seal(self.f['collection'], 'SCORE_SEAL.json', 'E37_COMPLETE')
        self.reject_before_labels()

    def test_tampered_sealed_scores_rejected(self):
        with (self.f['collection'] / 'scores.jsonl').open('a') as f:
            f.write('{}\n')
        self.reject_before_labels()

    def test_wrong_c2_donor_rejected(self):
        scores = copy.deepcopy(self.f['scores'])
        row = next(r for r in scores if r['control'] == 'opposite')
        row['donor_id'] = row['id']
        jsonl(self.f['collection'] / 'scores.jsonl', scores)
        seal(self.f['collection'], 'SCORE_SEAL.json', 'E37_COMPLETE')
        self.reject_before_labels()

    def test_wrong_pair_mean_nonfinite_or_pair_count_rejected(self):
        for values in ({'score': 3}, {'scores': [0]}, {'scores': [float('nan'), 0]}):
            scores = copy.deepcopy(self.f['scores'])
            scores[0].update(values)
            jsonl(self.f['collection'] / 'scores.jsonl', scores)
            seal(self.f['collection'], 'SCORE_SEAL.json', 'E37_COMPLETE')
            self.reject_before_labels()

    def test_incomplete_run_source_drift_and_input_mix_rejected(self):
        collection = self.f['collection']
        seal(collection, 'SCORE_SEAL.json', 'E37_INCOMPLETE')
        self.reject_before_labels()
        seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
        (self.f['here'] / 'runtime.py').write_text('modified source')
        self.reject_before_labels()

    def test_required_file_cannot_be_unsealed(self):
        path = self.f['collection'] / 'SCORE_SEAL.json'
        value = A.read(path)
        del value['files']['free.jsonl']
        A.dump(path, value)
        self.reject_before_labels()

    def test_late_or_unverified_checkpoint_rejected(self):
        collection = self.f['collection']
        receipt = A.read(collection / 'checkpoint_receipt.json')
        receipt['received_epoch'] = A.CHECKPOINT_ARRIVAL_DEADLINE + 1
        A.dump(collection / 'checkpoint_receipt.json', receipt)
        provenance = A.read(collection / 'provenance.json')
        provenance['checkpoint_receipt_sha256'] = A.sha(collection / 'checkpoint_receipt.json')
        A.dump(collection / 'provenance.json', provenance)
        seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
        self.reject_before_labels()

    def test_gate_hash_or_failed_parity_rejected(self):
        collection = self.f['collection']
        A.dump(collection / 'PARITY_RESULT.json', {'status': 'FAIL'})
        seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
        self.reject_before_labels()
        provenance = A.read(collection / 'provenance.json')
        provenance['parity_result_sha256'] = A.sha(collection / 'PARITY_RESULT.json')
        A.dump(collection / 'provenance.json', provenance)
        seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
        self.reject_before_labels()

    def test_missing_predecessor_completion_rejected(self):
        collection = self.f['collection']
        predecessors = A.read(collection / 'predecessors.json')
        predecessors['experiments']['E28']['status'] = 'NOT_RUN_ENVIRONMENT'
        A.dump(collection / 'predecessors.json', predecessors)
        provenance = A.read(collection / 'provenance.json')
        provenance['predecessors_sha256'] = A.sha(collection / 'predecessors.json')
        A.dump(collection / 'provenance.json', provenance)
        seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
        self.reject_before_labels()

    def test_claimed_pass_cannot_override_failed_numeric_gate(self):
        collection = self.f['collection']
        parity = A.read(collection / 'PARITY_RESULT.json')
        parity['smoke']['SFT']['max_abs_self_repeat_delta'] = .00011
        A.dump(collection / 'PARITY_RESULT.json', parity)
        provenance = A.read(collection / 'provenance.json')
        provenance['parity_result_sha256'] = A.sha(collection / 'PARITY_RESULT.json')
        A.dump(collection / 'provenance.json', provenance)
        seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
        self.reject_before_labels()

    def test_provider_budget_violation_rejected(self):
        collection = self.f['collection']
        run = A.read(collection / 'RUN.json')
        run['provider_elapsed_seconds_at_worker_exit'] = 5401
        A.dump(collection / 'RUN.json', run)
        seal(collection, 'SCORE_SEAL.json', 'E37_COMPLETE')
        self.reject_before_labels()


if __name__ == '__main__':
    unittest.main()
