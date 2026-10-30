import json
from pathlib import Path
import tempfile
import unittest

from projects.g_agreement.r_bench import remainder_r2 as r2


class TestRemainderR2(unittest.TestCase):
    def test_missing_arm_fails_loudly(self):
        with self.assertRaisesRegex(RuntimeError, 'SMOKE FAILED: missing nla/R-E'):
            r2.assert_arm_coverage([{'reader': 'olens', 'bank': 'R-E', 'n_rows': 1}], {('olens', 'R-E'), ('nla', 'R-E')}, ('reader', 'bank'))

    def test_zero_rows_do_not_pass(self):
        with self.assertRaisesRegex(RuntimeError, 'SMOKE FAILED'):
            r2.assert_arm_coverage([{'reader': 'nla', 'n_rows': 0}], {('nla',)}, ('reader',))

    def test_capture_contract_covers_all_72_arms(self):
        contract = r2.capture_smoke_contract()
        self.assertEqual(contract['cell_count'], 72)
        rows = [{**dict(zip(contract['dimensions'], c)), 'n_rows': 1} for c in contract['expected_cells']]
        r2.assert_arm_coverage(rows, set(contract['expected_cells']), contract['dimensions'])

    def test_fine_tuned_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'planted_facts/oracle_states/rf_x@sft'
            p.mkdir(parents=True)
            (p / 'read44_chat_index.json').write_text(json.dumps({'dataset': 'rf_x@sft', 'rows': [['same', 'A'], ['same', 'B']]}))
            banks = {'R-A': {'ids': {'same': {'split': 'test', 'dataset': 'x'}}}}
            rows = r2.inspect_taps(r2.discover_tap_roots(Path(tmp)), banks)
            self.assertEqual(rows[0]['source_kind'], 'fine_tuned_test_model')
            self.assertFalse(rows[0]['eligible_for_pool_probe'])

    def test_test_only_taps_are_insufficient(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'reader_states/olens/x'; p.mkdir(parents=True)
            (p / 'index.json').write_text(json.dumps({'reader': 'olens', 'dataset': 'x', 'item_ids': ['x:test']}))
            for block in (20, 32, 40):
                (p / f'chat_L44_rL{block}.npy').touch()
            rows = r2.inspect_taps([Path(tmp) / 'reader_states'], {'R-A': {'ids': {'x:test': {'split': 'test', 'dataset': 'x'}}}})
            self.assertEqual(rows[0]['tap_blocks'], [20, 32, 40])
            self.assertFalse(rows[0]['eligible_for_pool_probe'])

    def test_missing_bank_cannot_be_reported_as_missing_taps(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                r2.bank_inventory(Path(tmp), set())

    def test_defects_excluded_and_symlink_cycle_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for filename in r2.BANKS.values():
                (root / filename).write_text(json.dumps({'items': [{'dataset': 'bad', 'item_id': 'b', 'split': 'test'}, {'dataset': 'ok', 'item_id': 'k', 'split': 'pool'}]}))
            inventory = r2.bank_inventory(root, {'bad'})
            self.assertEqual(inventory['R-A']['facts'], ['ok'])
            self.assertEqual(inventory['R-A']['excluded'], ['bad'])
            (root / 'cycle').symlink_to(root, target_is_directory=True)
            self.assertEqual(r2.discover_tap_roots(root), [])


if __name__ == '__main__':
    unittest.main()
