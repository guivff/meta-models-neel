"""Synthetic TH-2 leakage/semantics regressions; no research outcome rows loaded."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from projects.g_agreement.r_bench import th2_forecast as F
from projects.g_agreement.r_bench import th2_preflight as P


def synthetic_cells():
    cells = []
    for fold in range(3):
        for label in (0, 1):
            patterns = np.ones(16)
            patterns[[0, 15]] += 4 + label + fold
            n = patterns.sum()
            cells.append(dict(dataset=f'fact{fold}', corpus=f'corpus{fold}', fold=fold,
                              label=label, p=(patterns @ F.BITS + .5) / (n + 1),
                              pairs=F.pair_counts(patterns), cal_n=n,
                              end=patterns.copy()))
    return cells


def target_fit(fits, fold=0, label=0):
    fit = next(x for x in fits if x['fold'] == fold and x['label'] == label)
    return {k: v for k, v in fit.items() if k not in ('quad_max_delta', 'marginal_max_error')}


class ForecastLeakageTest(unittest.TestCase):
    def test_endpoint_outcomes_do_not_enter_fit_or_prediction(self):
        cells = synthetic_cells()
        pred, fits = F.prediction(cells)
        changed = deepcopy(cells)
        for c in changed:
            c['end'] = np.zeros(16)
            c['end'][7] = 10000  # arbitrarily change pattern and endpoint sample size
        new_pred, new_fits = F.prediction(changed)
        self.assertEqual(fits, new_fits)
        for model in pred:
            np.testing.assert_array_equal(pred[model], new_pred[model])
        self.assertNotEqual(F.metrics(cells, pred)[0]['log_score'],
                            F.metrics(changed, new_pred)[0]['log_score'])

    def test_heldout_calibration_dependence_cannot_train_its_fold(self):
        cells = synthetic_cells()
        pred, fits = F.prediction(cells)
        changed = deepcopy(cells)
        c = changed[0]
        # Change dependence drastically while preserving n and all four marginals.
        patterns = np.zeros(16)
        patterns[[0, 15]] = c['cal_n'] / 2
        c['pairs'] = F.pair_counts(patterns)
        new_pred, new_fits = F.prediction(changed)
        self.assertEqual(target_fit(fits), target_fit(new_fits))
        np.testing.assert_array_equal(pred['factor'][0], new_pred['factor'][0])
        # The perturbation must be consequential in a fold where it is training data.
        a = np.array([target_fit(fits, 1)[r] for r in F.READERS])
        b = np.array([target_fit(new_fits, 1)[r] for r in F.READERS])
        self.assertGreater(np.linalg.norm(a-b), .01)

    def test_heldout_marginals_change_forecast_without_changing_loadings(self):
        cells = synthetic_cells()
        pred, fits = F.prediction(cells)
        changed = deepcopy(cells)
        changed[0]['p'] = np.array([.2, .35, .55, .7])
        new_pred, new_fits = F.prediction(changed)
        self.assertEqual(target_fit(fits), target_fit(new_fits))
        np.testing.assert_allclose(new_pred['factor'][0] @ F.BITS,
                                   changed[0]['p'], atol=1e-6)
        self.assertGreater(np.linalg.norm(pred['factor'][0] - new_pred['factor'][0]), .05)

    def test_empty_calibration_with_endpoint_weight_is_a_failed_draw(self):
        cells = synthetic_cells()
        cells[0]['cal_n'] = 0
        cells[0]['pairs'][:] = 0
        cells[0]['p'][:] = .5
        with self.assertRaisesRegex(ValueError, 'empty calibration'):
            F.prediction(cells)

    def test_bootstrap_warm_start_preserves_multistart(self):
        cells = synthetic_cells()
        fit = F.M.fit_factor
        with patch.object(F.M, 'fit_factor', wraps=fit) as tracked:
            F.prediction(cells, warm={f'{k}:{y}': np.zeros(4)
                                     for k in range(3) for y in (0, 1)})
        self.assertEqual(tracked.call_count, 6)
        self.assertTrue(all(call.kwargs.get('multistart') is True
                            for call in tracked.call_args_list))


class PreflightSemanticsTest(unittest.TestCase):
    def test_repeated_text_is_kept_in_one_half_corpus_and_fold(self):
        items = pd.DataFrame([
            {'dataset': '901_a', 'prompt_text': 'shared  document'},
            {'dataset': '902_b', 'prompt_text': ' shared\ndocument '},
            {'dataset': '903_c', 'prompt_text': 'unrelated'},
            {'dataset': '901_a', 'prompt_text': 'unique a'},
        ])
        got, groups = P.split_bank(items)
        for column in ['text_hash', 'half', 'corpus_group', 'fold']:
            self.assertEqual(got.loc[0, column], got.loc[1, column])
        self.assertEqual(got.loc[0, 'corpus_group'], got.loc[3, 'corpus_group'])
        # Reordering input rows cannot alter a document's assignment.
        permuted, _ = P.split_bank(items.iloc[::-1].reset_index(drop=True))
        expected = got.sort_values(['dataset', 'prompt_text']).reset_index(drop=True)
        actual = permuted.sort_values(['dataset', 'prompt_text']).reset_index(drop=True)
        pd.testing.assert_frame_equal(expected, actual)

    def test_end_to_end_semantics_votes_and_threshold_ties(self):
        with tempfile.TemporaryDirectory(prefix='th2_synthetic_') as directory:
            root = Path(directory)
            bank_dir = root/'projects/g_agreement/dataset'
            bank_dir.mkdir(parents=True)
            (root/'projects/g_agreement/manifest').mkdir(parents=True)
            cache = root/'cache/g_agreement/r'
            cache.mkdir(parents=True)
            results = root/'results/g_agreement/r'
            results.mkdir(parents=True)
            (results/'label_audit.csv').write_text('dataset,flagged\n901_two,False\n902_one,False\n')
            items = []
            scores = {}
            for dataset, sided, test_scores, pool_scores in [
                ('901_two', 'two', [-2, 1, 1, 3], [-1, 0]),
                ('902_one', 'one', [2, 4, 6, 8], [7, 9]),
            ]:
                for i, score in enumerate(test_scores+pool_scores):
                    label = i % 2
                    iid = f'{dataset}_{i}'
                    items.append(dict(dataset=dataset, item_id=iid, label=label,
                                      split='test' if i<4 else 'pool', tag='SURFACE',
                                      prompt_text=f'synthetic {iid}', system=False,
                                      primary=dict(candidates=['positive', 'negative'],
                                                   answer='positive' if label else 'negative',
                                                   sided=sided)))
                    scores[iid] = score
            bank_path = bank_dir/'items_r.json'
            bank_path.write_text(json.dumps(dict(items=items, meta={'sha256_items': 'synthetic'})))
            bank_hash = hashlib.sha256(bank_path.read_bytes()).hexdigest()
            (root/'projects/g_agreement/manifest/frozen_config_r.json').write_text(
                json.dumps({'items_sha256': {'items_r.json': bank_hash}}))
            rows = []
            for item in items:
                for reader in P.READERS:
                    score = scores[item['item_id']]
                    # Different lo and lp_A ensures primary_score selects the correct field.
                    lo = score if item['primary']['sided']=='two' else -score
                    lp_a = score if item['primary']['sided']=='one' else 10-score
                    rows.append(dict(key=f"{reader}|{item['item_id']}",
                        dataset=item['dataset'], item_id=item['item_id'], reader=reader,
                        layer=P.LAYERS[reader], render='chat', condition='natural', position='last',
                        label=item['label'], split=item['split'], sided=item['primary']['sided'],
                        state_item_id=item['item_id'], cand_A='positive', cand_B='negative',
                        lp_A=lp_a, lp_B=lp_a-lo, lo=lo, unscorable=False,
                        items_file='items_r.json', items_sha256=bank_hash, pod='A1',
                        git_sha=P.A.FROZEN_GIT_SHA, system=False))
            (cache/'reader_lo.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            with redirect_stdout(io.StringIO()):
                wide, metadata = P.run_preflight(root)
            self.assertTrue(metadata['semantic_joins_verified'])
            self.assertEqual(len(wide), 8)
            q = wide.set_index('item_id')
            expected = {
                '901_two': {'err': [0,1,0,0], 'literal_err': [0,0,1,0], 'pool_err': [0,0,1,0]},
                '902_one': {'err': [0,1,1,0], 'literal_err': [0,1,1,0], 'pool_err': [0,1,0,1]},
            }
            for ds, modes in expected.items():
                for mode, values in modes.items():
                    for reader in P.READERS:
                        actual = [q.loc[f'{ds}_{i}', f'{mode}_{reader}'] for i in range(4)]
                        self.assertEqual(actual, values, (ds, mode, reader))
            expanded = F.load_rows(results/'i2/th2_rows.csv.gz')
            self.assertEqual(set(expanded.convention), {'allmedian','literal','poolmedian'})
            self.assertEqual(expanded.groupby('convention').size().to_dict(),
                             dict(allmedian=8, literal=8, poolmedian=8))

if __name__ == '__main__':
    unittest.main(verbosity=2)


from pathlib import Path as _GuardPath
from projects.g_agreement.tests import _write_guard as WG
_GUARD_ROOT = _GuardPath(__file__).resolve().parents[3]
_GUARD = WG.ModuleWriteGuard([_GUARD_ROOT / "results" / "g_agreement", _GUARD_ROOT / "cache" / "g_agreement"])
_write_guard = _GUARD.fixture()

def test_zz_outputs_untouched():
    _GUARD.assert_clean()
