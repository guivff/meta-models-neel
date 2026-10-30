"""Synthetic separation/custody checks; no real scores or real guards."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cpu_join58 as C
import worker58 as W
from math58 import aggregate
from common58 import ARMS, SEEDS, dump, sha
from test58 import bank_fixture


def fixture():
    original = bank_fixture()
    pod, join = C.split_bank(original)
    rows = {r['key']: r for r in original['rows']}
    raw, legacy = [], []
    for row in pod['rows']:
        original_row = rows[join['row_map'][row['key']]]
        lookup = {x['id']: x for x in original_row['test']}
        for item in row['test']:
            original_item = lookup[join['item_map'][item['id']]['id']]
            for j in range(len(item['pairs'])):
                for arm in ARMS:
                    oriented = 8. if arm == 'none' else 4. if arm == 'J' else 6.
                    delta = oriented * (1 if original_item['label'] else -1)
                    raw.append({'row': row['key'], 'id': item['id'], 'pair_index': j, 'arm': arm,
                                'seed': SEEDS[int(arm[-1])] if arm.startswith('random') else None,
                                'logp_A': -10 + delta / 2, 'logp_B': -10 - delta / 2})
                    legacy.append({'row': original_row['key'], 'id': original_item['id'], 'pair_index': j,
                                   'arm': arm, 'logodds_A_minus_B': delta})
    return original, pod, join, raw, legacy


class BlindTests(unittest.TestCase):
    def test_no_labels_or_source_metadata_and_opaque_ids(self):
        original, pod, join, raw, legacy = fixture()
        W.validate_bank(pod)
        serialized = json.dumps(pod)
        for key in ('label', 'value', 'variant', 'category', 'control', 'source_seals', 'swap_donor_id'):
            self.assertNotIn('"' + key + '"', serialized)
        for row in original['rows']:
            self.assertNotIn(row['key'], serialized)
            for item in row['test']:
                self.assertNotIn(item['id'], serialized)

    def test_flipping_cpu_labels_does_not_change_pod_bytes(self):
        original = bank_fixture()
        flipped = copy.deepcopy(original)
        for row in flipped['rows']:
            for item in row['test']:
                item['label'] = 1 - item['label']
        self.assertEqual(C.split_bank(original)[0], C.split_bank(flipped)[0])

    def test_unknown_fields_rejected_at_every_data_level(self):
        pod, join = C.split_bank(bank_fixture())
        for level in ('root', 'row', 'dev', 'test', 'pair'):
            b = copy.deepcopy(pod)
            target = {'root': b, 'row': b['rows'][0], 'dev': b['rows'][0]['dev'][0],
                      'test': b['rows'][0]['test'][0], 'pair': b['rows'][0]['test'][0]['pairs'][0]}[level]
            target['label'] = 1
            with self.subTest(level=level), self.assertRaises(ValueError):
                W.validate_bank(b)

    def test_cpu_join_exactly_preserves_damage_rules_and_swaps(self):
        original, pod, join, raw, legacy = fixture()
        rows, converted = C.join_records(pod, join, raw)
        self.assertEqual(aggregate(rows, converted), aggregate(original['rows'], legacy))

    def test_missing_grid_and_duplicate_still_rejected_after_join(self):
        original, pod, join, raw, legacy = fixture()
        for bad in (raw[:-1], raw + [raw[-1]]):
            rows, converted = C.join_records(pod, join, bad)
            with self.assertRaises(ValueError):
                aggregate(rows, converted)

    def test_seed_identity_nonfinite_and_old_delta_schema_rejected(self):
        original, pod, join, raw, legacy = fixture()
        base = next(r for r in raw if r['arm'] == 'random0')
        changes = ({'seed': 0}, {'id': '0' * 32}, {'logp_A': float('nan')},
                   {'logp_B': .1}, {'pair_index': True}, {'label': 1})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                C.join_records(pod, join, [{**base, **change}])
        with self.assertRaises(ValueError):
            C.join_records(pod, join, [legacy[0]])

    def test_changed_candidate_or_join_mapping_rejected(self):
        original, pod, join, raw, legacy = fixture()
        bad = copy.deepcopy(pod); bad['rows'][0]['test'][0]['pairs'][0]['A_ids'] = [8]
        with self.assertRaises(ValueError):
            C.join_records(bad, join, raw)
        bad_join = copy.deepcopy(join)
        bad_join['item_map'][raw[0]['id']]['split'] = 'dev'
        with self.assertRaises(ValueError):
            C.join_records(pod, bad_join, raw)

    def test_pod_file_whitelist_rejects_extra_bank_files(self):
        pod, join = C.split_bank(bank_fixture())
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); dump(p / 'BANK.json', pod); (p / 'J384.npy').write_bytes(b'fixture basis')
            dump(p / 'INPUT_SEAL.json', {'experiment': 'E58b', 'schema': 'E58B_POD_INPUT_SEAL_V2',
                 'files': {n: sha(p / n) for n in ('BANK.json', 'J384.npy')}})
            W.validate_pod_directory(p)
            for name in ('items.PRIVATE.json', 'labels.DO_NOT_STAGE.jsonl', 'ANNOTATIONS.json', 'BOW_FITS.json'):
                extra = p / name; extra.write_text('{}')
                with self.subTest(name=name), self.assertRaises(ValueError):
                    W.validate_pod_directory(p)
                extra.unlink()

    def test_integrator_cpu_custody_receipt_is_required(self):
        original, pod, join, raw, legacy = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); here = root / 'results/e58b'; here.mkdir(parents=True)
            cache = root / 'cache/e58b'; folder = cache / 'cpu_only_v2'; folder.mkdir(parents=True)
            join['pod_input_seal_sha256'] = 'a' * 64
            dump(folder / 'CPU_JOIN.json', join)
            dump(folder / 'CPU_SEAL.json', {'files': {'CPU_JOIN.json': sha(folder / 'CPU_JOIN.json')}})
            binding = {'directory': str(folder.relative_to(root)), 'cpu_seal_sha256': sha(folder / 'CPU_SEAL.json'),
                       'cpu_join_sha256': sha(folder / 'CPU_JOIN.json')}
            dump(here / 'CPU_CUSTODY_BINDING.20261027.json', binding)
            request = {'cpu_custody_binding_sha256': sha(here / 'CPU_CUSTODY_BINDING.20261027.json')}
            with patch.object(C, 'ROOT', root), patch.object(C, 'HERE', here), patch.object(C, 'CACHE', cache):
                with self.assertRaises(FileNotFoundError):
                    C.load_custodied_join(request, pod, 'a' * 64)
                receipt = {'issuer': 'integrator', 'experiment': 'E58b', 'verified_cpu_only': True,
                           'labels_stayed_off_pod': True, 'pod_input_seal_sha256': 'a' * 64, **binding}
                dump(folder / 'INTEGRATOR_CUSTODY.json', receipt)
                self.assertEqual(C.load_custodied_join(request, pod, 'a' * 64)['original_bank'], original)
                receipt['issuer'] = 'W-sae'; (folder / 'INTEGRATOR_CUSTODY.json').write_text(json.dumps(receipt))
                with self.assertRaises(ValueError):
                    C.load_custodied_join(request, pod, 'a' * 64)


if __name__ == '__main__':
    unittest.main()
