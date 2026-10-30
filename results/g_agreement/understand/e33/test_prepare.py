"""CPU checks of frozen source reuse and complete tokenized E33 preparation."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import prepare
import reused

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
E12 = Path(os.environ.get('E33_TEST_E12', '/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e12'))
TOKENIZER = Path(os.environ.get('E33_TEST_TOKENIZER', '/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B'))
INPUTS = Path(os.environ.get('E33_TEST_INPUTS', str(ROOT / 'cache/g_agreement/understand/e33-inputs-v1')))


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def segments(source):
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef):
            result[node.name] = ast.get_source_segment(source, node)
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            result[node.targets[0].id] = ast.get_source_segment(source, node)
    return result


class FrozenSourceTests(unittest.TestCase):
    def test_reused_prompt_source_matches_pinned_ast_segments(self):
        manifest = prepare.read(HERE / 'UPSTREAM_SOURCE.json')
        local = segments((HERE / 'reused.py').read_text())
        for module in ['e12', 'e16']:
            for name, expected in manifest['segments'][module].items():
                self.assertEqual(digest(local[name]), expected, name)
        self.assertEqual(digest(reused.E16_BASE_SCORES_SOURCE), manifest['segments']['e16_worker']['base_scores'])

    def test_source_manifest_matches_exact_git_objects(self):
        manifest = prepare.read(HERE / 'UPSTREAM_SOURCE.json')
        for path, expected in manifest['files'].items():
            content = subprocess.check_output(['git', 'show', manifest['upstream_commit'] + ':' + path], cwd=ROOT)
            self.assertEqual(hashlib.sha256(content).hexdigest(), expected, path)

    def test_text_only_retains_placeholder_embedding(self):
        original, wrong = object(), object()
        self.assertIsNone(reused.activation_for('text_only', original, wrong))
        self.assertIs(reused.activation_for('activation_only', original, wrong), original)
        self.assertIs(reused.activation_for('text_wrong_activation', original, wrong), wrong)
        with self.assertRaises(ValueError):
            reused.activation_for('zero_vector', original, wrong)

    def test_context_message_is_exact_prefix_plus_native(self):
        text = 'A source whose punctuation is unfinished ('
        native = 'native carrier'
        self.assertEqual(reused.user_message(native, text, 'text_only'), reused.CONTEXT_PREFIX.format(text=text) + native)
        self.assertEqual(reused.user_message(native, text, 'activation_only'), native)

    def test_carrier_rejects_missing_or_duplicate_marker(self):
        class FakeTokenizer:
            def __init__(self, ids):
                self.ids = ids

            def apply_chat_template(self, messages, **kwargs):
                return self.ids

        for ids in [[1, 2], [1, 99, 99]]:
            with self.assertRaises(ValueError):
                reused.carrier(FakeTokenizer(ids), 'request', 'text', 'text_only', 99)
        self.assertEqual(reused.carrier(FakeTokenizer([1, 99, 2]), 'request', 'text', 'text_only', 99), ([1, 99, 2], 1))

    def test_seal_rejects_changes_and_parent_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'x.json').write_text('{}')
            prepare.dump(path / 'INPUT_SEAL.json', {'files': {'x.json': prepare.sha(path / 'x.json')}})
            prepare.verify(path)
            (path / 'x.json').write_text('{"changed":true}')
            with self.assertRaises(ValueError):
                prepare.verify(path)
            prepare.dump(path / 'INPUT_SEAL.json', {'files': {'../outside.json': 'x'}})
            with self.assertRaises(ValueError):
                prepare.verify(path)


@unittest.skipUnless(INPUTS.is_dir() and E12.is_dir() and TOKENIZER.is_dir(), 'Set E33_TEST_INPUTS/E12/TOKENIZER to staged frozen inputs for real-tokenizer equivalence checks')
class RealPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from transformers import AutoTokenizer
        cls.tok = AutoTokenizer.from_pretrained(TOKENIZER, local_files_only=True)
        cls.seal = prepare.verify(INPUTS)
        cls.items = prepare.records(INPUTS / 'items.input.jsonl')
        cls.source = prepare.records(E12 / 'items.input.jsonl')
        cls.templates = prepare.read(E12 / 'templates.json')
        cls.native = prepare.read(E12 / 'provenance.json')['native_carriers']['olens']

    def test_all_2100_prompt_heads_match_exact_upstream_functions(self):
        self.assertEqual(len(self.items), 2100)
        self.assertEqual([r['id'] for r in self.items], [r['id'] for r in self.source])
        for actual, source in zip(self.items, self.source):
            self.assertEqual(actual['feature'], source['feature'])
            self.assertEqual(actual['heads']['P1'], reused.base_head(self.tok, source['text']))
            head, slot = reused.carrier(self.tok, self.native['request'], source['text'], 'text_only', self.native['marker_token_id'])
            self.assertEqual(actual['heads']['P2'], head)
            self.assertEqual(actual['P2_placeholder_index'], slot)
            self.assertEqual(head.count(self.native['marker_token_id']), 1)

    def test_two_unchanged_phrasing_pairs_in_positive_first_order(self):
        self.assertEqual(prepare.sha(INPUTS / 'templates.json'), prepare.TEMPLATES_SHA)
        token_pairs = prepare.read(INPUTS / 'token_pairs.json')
        self.assertEqual(set(token_pairs), set(self.templates))
        for feature, spec in self.templates.items():
            self.assertEqual(token_pairs[feature], [[self.tok.encode(c, add_special_tokens=False) for c in p] for p in spec['olens']])
            self.assertEqual(len(token_pairs[feature]), 2)

    def test_units_cover_every_item_once_per_prompt_without_padding_heads(self):
        units = prepare.read(INPUTS / 'units.json')
        for prompt in ['P1', 'P2']:
            covered = []
            for unit in [u for u in units if u['prompt'] == prompt]:
                self.assertTrue(0 < len(unit['indices']) <= 16)
                covered.extend(unit['indices'])
                for i in unit['indices']:
                    self.assertEqual(self.items[i]['feature'], unit['feature'])
                    self.assertEqual(len(self.items[i]['heads'][prompt]), unit['head_length'])
            self.assertEqual(sorted(covered), list(range(2100)))

    def test_provenance_and_label_free_stage(self):
        provenance = prepare.read(INPUTS / 'provenance.json')
        self.assertEqual(provenance['e12_input_seal_sha256'], prepare.sha(E12 / 'INPUT_SEAL.json'))
        self.assertEqual(provenance['plan_sha256'], prepare.sha(HERE / 'PLAN.json'))
        self.assertEqual(provenance['upstream_source_sha256'], prepare.sha(HERE / 'UPSTREAM_SOURCE.json'))
        self.assertFalse(provenance['test_labels_staged'])
        self.assertFalse(provenance['activation_files_read_or_staged'])
        self.assertEqual(provenance['model_forwards'], 0)
        self.assertFalse(list(INPUTS.glob('*.npy')))
        for record in self.items:
            self.assertFalse({'label', 'y', 'value', 'cluster', 'activation'} & set(record))


if __name__ == '__main__':
    unittest.main()
