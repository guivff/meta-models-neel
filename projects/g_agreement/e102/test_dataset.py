"""Leakage and source-integrity checks for the E102 CPU dataset boundary."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from projects.g_agreement.e102.dataset import dev_rows, positions, finalize
from projects.g_agreement.e96.reconstructor_check import write,digest


class DatasetBoundaryTests(unittest.TestCase):
    def test_test_items_cannot_replace_missing_dev(self):
        items=[{'id':str(i),'split':'dev' if i<83 else 'test','feature':'x','ids':[1]} for i in range(84)]
        with self.assertRaisesRegex(ValueError,'84 dev'):dev_rows(items,['x'])

    def test_test_items_are_excluded_and_short_window_is_bounded(self):
        items=[{'id':str(i),'split':'dev','feature':'x','ids':[1,2,3]} for i in range(84)]
        items.append({'id':'test','split':'test','feature':'x','ids':[9]})
        self.assertEqual(len(dev_rows(items,['x'])),84)
        self.assertEqual(positions(items[0],8),[0,1,2])

    def test_duplicate_dev_id_rejected(self):
        items=[{'id':'same','split':'dev','feature':'x','ids':[1]} for _ in range(84)]
        with self.assertRaisesRegex(ValueError,'duplicate'):dev_rows(items,['x'])

    def test_finalizer_rejects_nondev_before_loading_vectors(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);plan=root/'plan';acq=root/'acq';gate=root/'gate'
            for d in (plan,acq,gate):d.mkdir()
            write(plan/'PAIRS.CPU.json',[{'split':'test'}])
            write(gate/'REPORT.json',{'status':'PASS','steps':10,'parity_byte_equal':3,'base_before_sha256':'a','base_after_sha256':'a','adapter_tensors_changed':1})
            def seal(d,name):write(d/name,{'files':{p.name:digest(p) for p in d.iterdir()}})
            seal(plan,'PLAN_SEAL.json');seal(gate,'OUTPUT_SEAL.json')
            write(acq/'ACQUISITION.json',{'plan_seal_sha256':digest(plan/'PLAN_SEAL.json'),'gate_seal_sha256':digest(gate/'OUTPUT_SEAL.json'),
                 'adapter_sha256':'7d4b301e002246af3c3f2bb6e768f8fa62f8aac2c231a0bd02a8d4f9ecafd9aa',
                 'base_revision':'6a9e13bd6fc8f0983b9b99948120bc37f49c13e9','capture_adapter_enabled':False,'block':44,
                 'decoding':{'do_sample':False,'max_new_tokens':128,'batch':1},'first_output_utc':'2026-10-28T16:00:00+00:00'})
            seal(acq,'OUTPUT_SEAL.json')
            with patch('projects.g_agreement.e102.dataset.np.load') as load:
                with self.assertRaisesRegex(ValueError,'non-dev'):finalize(plan,acq,gate,root/'out',root/'manifest.json')
                load.assert_not_called()
            self.assertFalse((root/'out').exists())
            (plan/'PAIRS.CPU.json').write_text('[]')
            with self.assertRaisesRegex(ValueError,'source seal mismatch'):finalize(plan,acq,gate,root/'out',root/'manifest.json')

if __name__=='__main__':unittest.main()
