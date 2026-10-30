"""CPU-only tests of freeze ordering and data boundaries, using synthetic inputs.

No E36 authored module, real tokenizer, W1 item or historical score is loaded.
"""
import argparse
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import build_bank as B


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.here = self.root / 'results/g_agreement/understand/e36'
        self.here.mkdir(parents=True)
        for name in ('build_bank', 'author_structure', 'author_content', 'check_structure', 'check_content'):
            (self.here / (name + '.py')).write_text('# synthetic source only\n')
        self.packet = {'experiment': 'E36', 'written_by': 'coordinator', 'rows': {
            row: {'values': ['a', 'b'], 'definition': 'synthetic test only',
                  'class': 'state-like' if i < 7 else ('count-like' if i < 16 else 'semantic')}
            for i, row in enumerate(B.ROWS)}}
        self.packet_path = self.here / 'ROW_DEFINITIONS.json'
        B.dump(self.packet_path, self.packet)
        self.packet_hash = B.sha(self.packet_path)
        self.tokenizer = self.root / 'fake_tokenizer'
        self.tokenizer.mkdir()
        (self.tokenizer / 'tokenizer.json').write_text('{}\n')
        self.out = self.here / 'cache' / 'synthetic'
        self.args = argparse.Namespace(definitions=str(self.packet_path),
                                       tokenizer=str(self.tokenizer), out=str(self.out), scope='expanded25')
        self.checks = 0
        self.loaded = []

    def loader(self, name):
        self.loaded.append(name)
        if name.startswith('author_'):
            return SimpleNamespace(render=lambda row, t, f, s: f'{row}|{t}|{f}|{s}')
        # The checker must not even be loaded before the whole raw bank is sealed.
        seal = B.read(self.out / 'BANK_SOURCE_SEAL.json')
        self.assertEqual(seal['files']['items.AUTHORED.jsonl'], B.sha(self.out / 'items.AUTHORED.jsonl'))
        self.assertEqual(len((self.out / 'items.AUTHORED.jsonl').read_text().splitlines()),
                         168 * (25 if self.args.scope == 'expanded25' else 8))
        def infer(row, text):
            self.checks += 1
            return {'value': ['a', 'b'][int(text.rsplit('|', 1)[1])], 'evidence': {'synthetic': True}}
        return SimpleNamespace(infer_label=infer)

    def run_build(self, loader=None, token_end_correct=True, token_lengths=(1, 1)):
        class FakeTokenizer:
            def __init__(self, **kwargs):
                pass
            def __call__(self, text, **kwargs):
                if kwargs != {'add_special_tokens': False, 'return_offsets_mapping': True}:
                    raise AssertionError('unexpected tokenizer framing')
                count = token_lengths[int(text.rsplit('|', 1)[1])]
                offsets = [(0, 0)] * (count - 1) + [(0, len(text) if token_end_correct else len(text)-1)]
                return {'input_ids': [1] * count, 'offset_mapping': offsets}
        with patch.object(B, 'HERE', self.here), patch.object(B, 'ROOT', self.root), \
             patch.object(B, 'load_module', loader or self.loader), \
             patch.object(B, 'TOKENIZER_SHA', B.sha(self.tokenizer / 'tokenizer.json')), \
             patch.object(B, 'DEFINITION_SHA', self.packet_hash), \
             patch.dict('sys.modules', {'transformers': SimpleNamespace(PreTrainedTokenizerFast=FakeTokenizer)}):
            return B.build(self.args)

    def test_complete_freeze_before_check_and_label_free_stage(self):
        result = self.run_build()
        self.assertEqual(result['label_checks_passed'], 4200)
        self.assertEqual(self.checks, 4200)
        stage = [json.loads(s) for s in (self.out / 'items.input.jsonl').read_text().splitlines()]
        self.assertTrue(all(set(s) == {'id', 'feature', 'split', 'cluster', 'text', 'ids'} for s in stage))
        receipt = B.read(self.out / 'FREEZE_RECEIPT.json')
        self.assertEqual(receipt['bank_sha256'], B.sha(self.out / 'items.input.jsonl'))
        self.assertEqual(receipt['automatic_label_check']['status'], 'PASS')
        for name, expected in B.read(self.out / 'PREPARED_SEAL.json')['files'].items():
            self.assertEqual(B.sha(self.out / name), expected)

    def test_failed_check_retains_full_bank_and_blocks_stage(self):
        def loader(name):
            module = self.loader(name)
            if name.startswith('check_'):
                module.infer_label = lambda row, text: {'value': 'wrong', 'evidence': {}}
            return module
        with self.assertRaisesRegex(ValueError, 'failed automatic labels'):
            self.run_build(loader)
        self.assertEqual(B.read(self.out / 'LABEL_CHECK.json')['status'], 'FAIL')
        self.assertEqual(B.read(self.out / 'LABEL_CHECK.json')['items_checked'], 4200)
        self.assertTrue((self.out / 'BANK_SOURCE_SEAL.json').exists())
        self.assertFalse((self.out / 'items.input.jsonl').exists())
        self.assertFalse((self.out / 'FREEZE_RECEIPT.json').exists())

    def test_frozen_output_never_overwritten(self):
        self.run_build()
        before = B.sha(self.out / 'BANK_SOURCE_SEAL.json')
        with self.assertRaisesRegex(ValueError, 'never overwrite'):
            self.run_build()
        self.assertEqual(B.sha(self.out / 'BANK_SOURCE_SEAL.json'), before)

    def test_authorization_gate_precedes_module_load(self):
        self.packet['experiment'] = 'PENDING'
        self.packet_path.write_text(json.dumps(self.packet))
        self.packet_hash = B.sha(self.packet_path)
        with self.assertRaisesRegex(ValueError, 'authorized row-definition'):
            self.run_build()
        self.assertEqual(self.loaded, [])
        self.assertFalse(self.out.exists())

    def test_no_raw_outputs_outside_cache(self):
        self.args.out = str(self.here / 'accidental-tracked-bank')
        with self.assertRaisesRegex(ValueError, 'ignored cache'):
            self.run_build()
        self.assertEqual(self.loaded, [])

    def test_tokenizer_read_position_failure_keeps_authored_freeze(self):
        with self.assertRaisesRegex(ValueError, 'final-token read position'):
            self.run_build(token_end_correct=False)
        self.assertEqual(B.read(self.out / 'LABEL_CHECK.json')['status'], 'PASS')
        self.assertFalse((self.out / 'FREEZE_RECEIPT.json').exists())

    def test_original_eight_row_scope_preserved(self):
        self.args.scope = 'original8'
        result = self.run_build()
        self.assertEqual(result['items'], 1344)
        receipt = B.read(self.out / 'FREEZE_RECEIPT.json')
        self.assertEqual(set(receipt['rows']), set(B.FALLBACK_ROWS))
        self.assertEqual(receipt['automatic_length_check']['checked'], 672)

    def test_definition_packet_mutation_precedes_author_load(self):
        self.packet_path.write_text(self.packet_path.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'definition packet SHA256 mismatch'):
            self.run_build()
        self.assertEqual(self.loaded, [])

    def test_expanded_bank_length_check_covers_every_pair(self):
        self.run_build()
        check = B.read(self.out / 'LENGTH_CHECK.json')
        self.assertEqual(check['pairs_checked'], 2100)
        self.assertEqual(check['maximum_ratio'], 1.0)
        self.assertEqual(check['status'], 'PASS')

    def test_length_failure_preserves_bank_and_blocks_capture_receipt(self):
        with self.assertRaisesRegex(ValueError, 'automatic length matching'):
            self.run_build(token_lengths=(10, 12))
        self.assertEqual(B.read(self.out / 'LENGTH_CHECK.json')['status'], 'FAIL')
        self.assertTrue((self.out / 'BANK_SOURCE_SEAL.json').exists())
        self.assertFalse((self.out / 'FREEZE_RECEIPT.json').exists())

    def test_ten_percent_boundary_is_accepted(self):
        self.run_build(token_lengths=(10, 11))
        self.assertEqual(B.read(self.out / 'LENGTH_CHECK.json')['status'], 'PASS')

    def test_dynamic_checker_import_supports_dataclass_annotations(self):
        (self.here / 'check_content.py').write_text(
            'from __future__ import annotations\nfrom dataclasses import dataclass\n'
            '@dataclass\nclass Checked:\n    value: int\n')
        with patch.object(B, 'HERE', self.here):
            module = B.load_module('check_content')
        self.assertEqual(module.Checked(4).value, 4)

    def test_import_failure_resumes_exact_frozen_bank_without_authors(self):
        def fail_import(name):
            if name.startswith('check_'):
                raise ImportError('synthetic checker import failure')
            return self.loader(name)
        with self.assertRaises(ImportError):
            self.run_build(fail_import)
        original_bank = B.sha(self.out / 'items.AUTHORED.jsonl')
        original_seal = B.sha(self.out / 'BANK_SOURCE_SEAL.json')
        (self.here / 'build_bank.py').write_text('# synthetic operational import repair\n')
        self.args.resume_frozen_import_failure = True
        def resume_loader(name):
            self.assertTrue(name.startswith('check_'), 'resume must never load a generator')
            return self.loader(name)
        self.run_build(resume_loader)
        self.assertEqual(B.sha(self.out / 'items.AUTHORED.jsonl'), original_bank)
        self.assertEqual(B.sha(self.out / 'BANK_SOURCE_SEAL.json'), original_seal)
        receipt = B.read(self.out / 'OPERATIONAL_RESUME.json')
        self.assertEqual(receipt['prior_item_labels_checked'], 0)
        self.assertEqual(receipt['items_replaced_or_dropped'], 0)

    def test_import_recovery_refuses_checker_changes(self):
        def fail_import(name):
            if name.startswith('check_'):
                raise ImportError('synthetic checker import failure')
            return self.loader(name)
        with self.assertRaises(ImportError):
            self.run_build(fail_import)
        (self.here / 'check_content.py').write_text('# changed checker\n')
        self.args.resume_frozen_import_failure = True
        with self.assertRaisesRegex(ValueError, 'changed author/checker'):
            self.run_build()


if __name__ == '__main__':
    unittest.main()
