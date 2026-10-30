"""Synthetic regression checks for native eligibility and wave isolation."""
import copy
import unittest
from sources67_wave2 import validate_native
from packet67 import build_packets
from test67 import pool


class Wave2Tests(unittest.TestCase):
    def case(self, reader='nla'):
        unit = {'id': 'test0', 'feature': 'row', 'split': 'test', 'text': 'exact prompt'}
        job = {'kind': 'native', 'reader': reader, 'units': [unit]}
        row = {'unit_id': 'test0', 'id': 'test0:'+reader+':0', 'reader': reader, 'repeat': 0,
               'feature': 'row', 'reader_native_layer': 42 if reader == 'nla' else 44, 'text': ''}
        return job, [row], {'test0': copy.deepcopy(unit)}

    def test_both_native_layers_and_empty_readout_retained(self):
        for reader in ('oracle', 'nla'): validate_native(*self.case(reader))

    def test_injections_repeats_wrong_layers_and_non_test_rejected(self):
        for field, value in [('kind', 'injection'), ('reader', 'other')]:
            job, rows, items = self.case(); job[field] = value
            with self.assertRaises(ValueError): validate_native(job, rows, items)
        for field, value in [('repeat', 1), ('reader_native_layer', 44), ('unit_id', 'other'), ('feature', 'other')]:
            job, rows, items = self.case(); rows[0][field] = value
            with self.assertRaises(ValueError): validate_native(job, rows, items)
        job, rows, items = self.case(); job['units'][0]['split'] = 'dev'
        with self.assertRaises(ValueError): validate_native(job, rows, items)

    def test_exact_prompt_and_cardinality_enforced(self):
        job, rows, items = self.case(); items['test0']['text'] = 'changed'
        with self.assertRaises(ValueError): validate_native(job, rows, items)
        job, rows, items = self.case()
        with self.assertRaises(ValueError): validate_native(job, [], items)

    def test_four_strata_wave_separate_determinism(self):
        pools = {(b, r): pool(b, r) for b in ('E56', 'E57') for r in ('oracle', 'nla')}
        packets, mapping, inventory = build_packets(pools)
        self.assertEqual(list(map(len, packets)), [400, 400])
        self.assertEqual(len(mapping), 400)
        self.assertTrue(all(x['sampled_items'] == 100 for x in inventory))
        self.assertEqual((packets, mapping, inventory), build_packets(pools))


if __name__ == '__main__': unittest.main()
