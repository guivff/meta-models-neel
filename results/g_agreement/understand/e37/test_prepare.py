"""CPU checks for the sealed E37 population, frozen prompt pairs and parity boundary."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('e37_prepare', HERE / 'prepare.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
INPUTS = p.ROOT / 'cache/g_agreement/understand/e37-inputs-v1'
W1 = Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/blindspot/w1-readonly-20261024')
TOKENIZER = Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B')


class PreparationUnits(unittest.TestCase):
    def test_source_pin_rejects_modified_bytes_and_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'data').write_text('frozen')
            refs = {'files': {'fixture': {'data': p.sha(folder / 'data')}}}
            p.check_sources({'fixture': folder}, refs)
            (folder / 'data').write_text('drift')
            with self.assertRaisesRegex(ValueError, 'frozen source mismatch'):
                p.check_sources({'fixture': folder}, refs)
            with self.assertRaisesRegex(ValueError, 'frozen source mismatch'):
                p.check_sources({'fixture': folder}, {'files': {'fixture': {'../escape': 'irrelevant'}}})

    def test_smoke_selection_ignores_labels_and_order(self):
        items = [{'id': str(i), 'feature': str(i % 25), 'label': i % 2, 'score': i} for i in range(2100)]
        changed = [dict(r, label=1-r['label'], score=-r['score']) for r in items[::-1]]
        self.assertEqual(p.smoke_ids(items), p.smoke_ids(changed))
        self.assertEqual(len(set(p.smoke_ids(items))), 20)

    def test_auc_ties_and_direction(self):
        self.assertEqual(p.auc([0, 1, 1, 2], [0, 0, 1, 1]), .875)
        self.assertEqual(p.auc([0, 1], [1, 0]), 0)
        with self.assertRaises(ValueError):
            p.auc([float('nan'), 1], [0, 1])

    def test_frozen_e15_validity_cannot_be_reselected(self):
        metrics = p.read(p.ROOT / p.SOURCE_NAMES['metrics'])
        candidates = p.read(p.ROOT / p.SOURCE_NAMES['candidates'])
        pairs = p.read(p.ROOT / p.SOURCE_NAMES['pairs'])
        w1 = p.read(p.ROOT / 'cache/g_agreement/understand/e33-inputs-v1/templates.json')
        selected = p.select_templates(w1, candidates, pairs, metrics, sorted(w1))
        self.assertEqual(set(selected['C2']), set(p.C2_ROWS))
        modified = deepcopy(metrics)
        modified['rows'][0]['valid_pairs'] = [0]
        with self.assertRaisesRegex(ValueError, 'validity mask changed'):
            p.select_templates(w1, candidates, pairs, modified, sorted(w1))
        modified = deepcopy(candidates)
        modified['values']['prose_paren'].reverse()
        with self.assertRaisesRegex(ValueError, 'orientation differs'):
            p.select_templates(w1, modified, pairs, metrics, sorted(w1))


@unittest.skipUnless((INPUTS / 'INPUT_SEAL.json').exists(), 'generate immutable E37 inputs first')
class PreparedArtifact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = p.records(INPUTS / 'items.input.jsonl')
        cls.templates = p.read(INPUTS / 'templates.json')
        cls.tokens = p.read(INPUTS / 'token_pairs.json')

    def test_seal_and_no_unsealed_files(self):
        seal = p.read(INPUTS / 'INPUT_SEAL.json')
        self.assertEqual(set(seal['files']), {x.name for x in INPUTS.iterdir()} - {'INPUT_SEAL.json'})
        for name, digest in seal['files'].items():
            self.assertEqual(p.sha(INPUTS / name), digest)
        self.assertEqual(seal['status'], 'E37_INPUTS_FROZEN_BEFORE_MODEL_LOAD')

    def test_population_and_labels_boundary(self):
        self.assertEqual(len(self.items), 2100)
        self.assertEqual(len({r['id'] for r in self.items}), 2100)
        self.assertEqual(p.Counter(r['feature'] for r in self.items), p.Counter({f: 84 for f in self.templates['C1']}))
        for item in self.items:
            self.assertEqual(set(item), {'id', 'feature', 'donor_id'})
        labels = p.read(INPUTS / 'parity_labels.json')
        self.assertEqual(set(labels), {r['id'] for r in self.items if r['feature'] in p.PARITY_ROWS})
        self.assertEqual(len(labels), 252)
        self.assertEqual(set(labels.values()), {0, 1})
        self.assertFalse(any('DO_NOT_STAGE' in x.name for x in INPUTS.iterdir()))

    def test_smoke_and_reference_pins(self):
        frozen = p.read(HERE / 'SMOKE_SET.json')
        gate = p.read(INPUTS / 'parity_inputs.json')
        self.assertEqual(p.smoke_ids(self.items), frozen['selected_ids'])
        self.assertEqual(gate['smoke_ids'], frozen['selected_ids'])
        self.assertEqual(gate['smoke_set_sha256'], p.sha(HERE / 'SMOKE_SET.json'))
        self.assertEqual(gate['rl_reference_auc'], {
            'prose_sentiment': .9109977324263039, 'prose_paren': .4846938775510204,
            'python_string': .6439909297052154})
        self.assertEqual(frozen['population_count'], 2100)
        self.assertEqual(frozen['population_rows'], 25)

    def test_reciprocal_donor_and_native_pair_tokens(self):
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(TOKENIZER, local_files_only=True)
        lookup = {r['id']: r for r in self.items}
        for item in self.items:
            donor = lookup[item['donor_id']]
            self.assertEqual(donor['donor_id'], item['id'])
            self.assertEqual(donor['feature'], item['feature'])
        for channel, features in self.templates.items():
            for feature, pairs in features.items():
                self.assertEqual(self.tokens[channel][feature],
                                 [[tok.encode(c, add_special_tokens=False) for c in pair] for pair in pairs])
        expected = p.read(p.ROOT / p.SOURCE_NAMES['candidates'])['candidates']
        for feature in self.templates['C1prime']:
            self.assertEqual(self.templates['C1prime'][feature], expected[feature])

    def test_native_carrier_exact_original(self):
        from transformers import AutoTokenizer
        import sys
        sys.path.insert(0, str(p.ROOT / 'external/mats-nla-workspace/src'))
        from mats.readers.olens import OracleLens
        tok = AutoTokenizer.from_pretrained(TOKENIZER, local_files_only=True)
        head, slot = OracleLens(model=None, tok=tok, device='cpu').carrier(44)
        carrier = p.read(INPUTS / 'carrier.json')
        self.assertEqual(carrier['head_ids'], head)
        self.assertEqual(carrier['marker_index'], slot)
        self.assertEqual(carrier['marker_token_id'], 158983)
        self.assertEqual(carrier['alpha'], 16000)
        self.assertEqual(carrier['prefix_ids'], {'C1': [], 'C1prime': [], 'C2': tok.encode('- ', add_special_tokens=False), 'C4': []})

    def test_activations_exact_canonical_capture_by_id(self):
        target = W1 / 'w1-assembled/target'
        original = np.load(target / 'acts44.npy', mmap_mode='r')
        order = {item_id: i for i, item_id in enumerate(p.read(target / 'items.order.json'))}
        actual = np.load(INPUTS / 'acts44.npy', mmap_mode='r')
        self.assertEqual(actual.shape, (2100, 5120))
        self.assertEqual(actual.dtype, np.float32)
        for index, item in enumerate(self.items):
            self.assertTrue(np.array_equal(actual[index], original[order[item['id']]]))

    def test_provenance_plan_sources_and_no_models(self):
        provenance = p.read(INPUTS / 'provenance.json')
        self.assertEqual(provenance['plan_sha256'], p.sha(HERE / 'PLAN.json'))
        self.assertEqual(provenance['source_references_sha256'], p.sha(HERE / 'SOURCE_REFERENCES.json'))
        self.assertEqual(provenance['source_files'], p.read(HERE / 'SOURCE_REFERENCES.json')['files'])
        self.assertEqual(provenance['parity_labels_staged'], 252)
        self.assertEqual(provenance['other_private_labels_staged'], 0)
        self.assertEqual(provenance['model_loads'], 0)
        self.assertEqual(provenance['model_forwards'], 0)


if __name__ == '__main__':
    unittest.main()
