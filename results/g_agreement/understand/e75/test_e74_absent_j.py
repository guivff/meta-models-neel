"""Temporary synthetic repositories and captures only."""
import copy
from datetime import datetime, timezone
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from e74_absent_j import build, digest, publish, RECORD


class AbsentJTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.p = Path(self.temp.name)
        self.env = dict(os.environ, GIT_AUTHOR_DATE='2026-10-26T10:00:00Z',
                        GIT_COMMITTER_DATE='2026-10-26T10:00:00Z')
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic fixture')
        self.git('config', 'user.email', 'synthetic@example.invalid')
        (self.p / 'card.md').write_text('Synthetic feasible GLM, no public J checkpoint.\n')
        self.write('categories.json', {'rows': [{'row': 'W1/col', 'category': 'bookkeeping'},
                                               {'row': 'E36/topic', 'category': 'content'}]})
        self.git('add', 'card.md', 'categories.json')
        self.git('commit', '-qm', 'Synthetic frozen sources')
        card = self.committed('card.md')
        cats = self.committed('categories.json')
        self.write('verdict.json', {'verdict': 'FEASIBLE', 'j_lens_available': False, 'source_card': card})
        self.git('add', 'verdict.json'); self.git('commit', '-qm', 'Synthetic asset verdict')
        rows = self.write('rows.json', {'rows': [{'row': 'W1/col'}, {'row': 'E36/topic'}]})
        inputs = self.write('input.json', {'files': {'rows.json': rows['sha256']}})
        (self.p / 'acts.bin').write_bytes(b'synthetic-capture-not-real')
        capture = self.write('capture.json', {'track': 'G', 'sealed_at': '2026-10-27T10:00:00Z',
            'input_seal_sha256': inputs['sha256'], 'files': {'acts.bin': digest((self.p / 'acts.bin').read_bytes())}})
        receipt = self.write('receipt.json', {'issuer': 'I-2', 'checked_at': '2026-10-27T10:01:00Z',
            'capture_seal_sha256': capture['sha256'], 'asset_card_sha256': card['sha256'],
            'j_lens_public': False, 'go_issued': False, 'reader_outputs_accessed': False,
            'readers_held_until_record_commit': True})
        self.plan = {'experiment': 'E74', 'input_seal': inputs, 'capture_seal': capture,
                     'input_rows_member': 'rows.json', 'category_binding': cats,
                     'asset_verdict': self.committed('verdict.json'), 'custody_availability_receipt': receipt}
        self.now = datetime(2026, 10, 27, 10, 2, tzinfo=timezone.utc)

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.p, env=self.env, stderr=subprocess.DEVNULL, text=True).strip()

    def committed(self, name):
        return dict(repo=str(self.p), commit=self.git('rev-parse', 'HEAD'), path=name,
                    sha256=digest((self.p / name).read_bytes()))

    def write(self, name, obj):
        path = self.p / name
        path.write_text(json.dumps(obj))
        return {'path': str(path), 'sha256': digest(path.read_bytes())}

    def test_bound_record_and_exact_baseline(self):
        out = build(self.plan, self.now)
        self.assertEqual(out['record'], RECORD)
        self.assertTrue(out['rg2_not_evaluable_permanent'])
        self.assertIsNone(out['J_forecast'])
        self.assertIsNone(out['J_null_median'])
        self.assertEqual([(r['row'], r['prediction']) for r in out['category_forecast']],
                         [('E36/topic', 'REPORTED'), ('W1/col', 'MISSED')])

    def test_missing_or_tampered_capture_refused(self):
        (self.p / 'acts.bin').write_bytes(b'changed')
        with self.assertRaises(ValueError): build(self.plan, self.now)
        (self.p / 'acts.bin').unlink()
        with self.assertRaises(FileNotFoundError): build(self.plan, self.now)

    def test_open_readers_go_or_public_j_refused(self):
        for field in ['go_issued', 'reader_outputs_accessed', 'j_lens_public']:
            plan = copy.deepcopy(self.plan)
            receipt = json.loads((self.p / 'receipt.json').read_text())
            receipt[field] = True
            plan['custody_availability_receipt'] = self.write('modified_receipt.json', receipt)
            with self.assertRaises(ValueError): build(plan, self.now)

    def test_category_omission_refused(self):
        self.write('categories.json', {'rows': [{'row': 'W1/col', 'category': 'bookkeeping'}]})
        self.git('add', 'categories.json'); self.git('commit', '-qm', 'Synthetic missing category')
        self.plan['category_binding'] = self.committed('categories.json')
        with self.assertRaises(ValueError): build(self.plan, self.now)

    def test_wrong_committed_source_hash_refused(self):
        self.plan['asset_verdict']['sha256'] = '0' * 64
        with self.assertRaises(ValueError): build(self.plan, self.now)

    def test_captured_ordinals_are_listed_not_binarised_or_forecast(self):
        rows = self.write('rows.json', {'rows': [{'row': r} for r in
            ['W1/col', 'E36/topic', 'W1/python_depth_ordinal', 'W1/table_column_ordinal']]})
        self.plan['input_seal'] = self.write('input.json', {'files': {'rows.json': rows['sha256']}})
        capture = json.loads((self.p / 'capture.json').read_text())
        capture['input_seal_sha256'] = self.plan['input_seal']['sha256']
        self.plan['capture_seal'] = self.write('capture.json', capture)
        receipt = json.loads((self.p / 'receipt.json').read_text())
        receipt['capture_seal_sha256'] = self.plan['capture_seal']['sha256']
        self.plan['custody_availability_receipt'] = self.write('receipt.json', receipt)
        out = build(self.plan, self.now)
        self.assertEqual(len(out['category_forecast']), 2)
        self.assertEqual(len(out['captured_units']), 4)
        self.assertEqual([r['row'] for r in out['confirmatory_exclusions']],
                         ['W1/python_depth_ordinal', 'W1/table_column_ordinal'])
        self.assertTrue(all(r['capture_retained'] for r in out['confirmatory_exclusions']))

    def test_exclusive_claim_retained_and_no_overwrite(self):
        out = build(self.plan, self.now)
        target = self.p / 'out.json'; claim = self.p / 'once.json'
        publish(out, target, claim)
        original = target.read_bytes()
        with self.assertRaises(ValueError): publish(out, target, claim)
        self.assertEqual(original, target.read_bytes())
        with self.assertRaises(FileExistsError): publish(out, self.p / 'other.json', claim)
        self.assertFalse((self.p / 'other.json').exists())

    def test_i2_pinned_reader_admission_accepts_committed_record(self):
        # Run only its reader-custody check, never compute/budget/admission actions.
        root = Path(__file__).resolve().parents[4]
        source = subprocess.check_output(['git', 'show',
            'e6370bd457e79765e869ffdb007b5343481a7512:projects/g_agreement/i2/admission.py'], cwd=root)
        module_path = self.p / 'i2_pinned.py'; module_path.write_bytes(source)
        spec = importlib.util.spec_from_file_location('i2_pinned', module_path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        record = build(self.plan, self.now)
        self.write('out.json', record)
        self.env.update(GIT_AUTHOR_DATE='2026-10-27T10:03:00Z', GIT_COMMITTER_DATE='2026-10-27T10:03:00Z')
        self.git('add', 'out.json'); self.git('commit', '-qm', 'Synthetic pre-GO record')
        request = {'track': 'G', 'capture_seal': self.plan['capture_seal'],
                   'input_seal': self.plan['input_seal'], 'forecast': self.committed('out.json'),
                   'asset_card': self.plan['asset_verdict'],
                   'rows': [{'row': 'W1/col', 'category': 'bookkeeping'},
                            {'row': 'E36/topic', 'category': 'content'}]}
        module.validate_readers(request, datetime(2026, 10, 27, 10, 4, tzinfo=timezone.utc))


if __name__ == '__main__':
    unittest.main()
