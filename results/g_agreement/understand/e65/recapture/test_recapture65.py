"""CPU synthetic recapture tests; no source items, probes or reader outcomes."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
import common65 as C
import worker65 as W
from preflight65 import archive_members


def fixture():
    items = []; offset = 0
    for i in range(20):
        ids = [i+1, i+2]
        items.append({'id': f'{i:032x}', 'ids': ids, 'start': 0, 'stop': 2, 'offset': offset}); offset += 2
    return {'experiment': 'E65', 'schema': 'E65_BLIND_RECAPTURE_V1', 'rows': [{'key': 'a'*32, 'items': items}]}


class Model(torch.nn.Module):
    def __init__(self, tuple_output=True):
        super().__init__(); self.layer = torch.nn.Identity(); self.tuple_output = tuple_output; self.after_hook = False
    def forward(self, input_ids, attention_mask, **kwargs):
        h = (input_ids.float()*attention_mask).cumsum(1)[:,:,None].expand(-1,-1,4)
        out = self.layer((h,) if self.tuple_output else h)
        self.after_hook = True; return out


class RecaptureTests(unittest.TestCase):
    def test_raw_ragged_capture_fp16_offsets_and_early_stop(self):
        items = [{'ids':[1,2,3], 'start':1, 'stop':3}, {'ids':[4,5], 'start':0, 'stop':2}]
        for tup in (False, True):
            model = Model(tup); values = W.capture_batch(model, model.layer, items, 'cpu', dim=4)
            np.testing.assert_array_equal(values[0], np.array([[3]*4,[6]*4], dtype=np.float16))
            np.testing.assert_array_equal(values[1], np.array([[4]*4,[9]*4], dtype=np.float16))
            self.assertFalse(model.after_hook); self.assertFalse(model.layer._forward_hooks)
            self.assertEqual(values[0].dtype, np.float16)

    def test_capture_invalid_shape_cleans_hook(self):
        model = Model()
        with self.assertRaises(ValueError): W.capture_batch(model, model.layer, [{'ids':[1], 'start':0, 'stop':1}], 'cpu', dim=5)
        self.assertFalse(model.layer._forward_hooks)

    def test_exact_20_items_and_contiguous_offsets(self):
        bank = fixture(); items, count = C.validate_bank(bank)
        self.assertEqual((len(items), count), (20, 40))
        for mutate in (lambda x:x['rows'][0]['items'].pop(),
                       lambda x:x['rows'][0]['items'][1].update(offset=0),
                       lambda x:x['rows'][0]['items'][1].update(id=x['rows'][0]['items'][0]['id']),
                       lambda x:x['rows'][0]['items'][0].update(stop=1),
                       lambda x:x['rows'][0]['items'][0].update(ids=[True,2])):
            bad=copy.deepcopy(bank); mutate(bad)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError): C.validate_bank(bad)

    def test_unknown_label_metadata_rejected_at_each_level(self):
        for level in ('root','row','item'):
            bank=fixture(); target=bank if level=='root' else bank['rows'][0] if level=='row' else bank['rows'][0]['items'][0]
            target['label']=1
            with self.subTest(level=level), self.assertRaises(ValueError): C.validate_bank(bank)

    def test_only_two_data_files_allowed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(C, 'CACHE', Path(tmp)):
            folder=Path(tmp)/'pod_inputs';folder.mkdir();C.dump(folder/'BANK.json',fixture())
            C.dump(folder/'INPUT_SEAL.json',{'experiment':'E65','schema':'E65_INPUT_SEAL_V1','files':{'BANK.json':C.sha(folder/'BANK.json')}})
            self.assertEqual(C.load_inputs()[2],40)
            (folder/'extra.json').write_text('{}')
            with self.assertRaises(ValueError):C.load_inputs()

    def test_memory_headroom_and_full_work_forecast(self):
        gb=1024**3
        self.assertTrue(W.memory_safe(140*gb,30*gb,100*gb));self.assertFalse(W.memory_safe(140*gb,3*gb,100*gb))
        items=[{'ids':[1]*i} for i in range(1,70)];chunks=C.batches(items,32)
        self.assertEqual(sum(map(len,chunks)),len(items))
        self.assertGreaterEqual(W.forecast(chunks,[{'median_seconds':1.,'sequences':32,'max_tokens':32}]),len(chunks))

    def test_1080_second_own_pod_cap(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(W,'HERE',Path(tmp)),patch.object(W,'CACHE',Path(tmp)):
            p=Path(tmp);(p/'pod_inputs').mkdir()
            for n in ('LAUNCH_REQUEST.json','POD_SOURCE_SEAL.json','pod_inputs/INPUT_SEAL.json'):(p/n).write_text('{}')
            request={'source_seal_sha256':C.sha(p/'POD_SOURCE_SEAL.json'),'input_seal_sha256':C.sha(p/'pod_inputs/INPUT_SEAL.json')}
            a={'issuer':'integrator','experiment':'E65','gpu_count':1,'pod_id':'own','source_pushed':True,'external_hardstop_verified':True,
               'hold_renewer_verified':True,'separate_pod_verified':True,'source_commit':'a'*40,'request_sha256':C.sha(p/'LAUNCH_REQUEST.json'),
               **request,'provider_created_epoch':0,'previous_gpu_seconds':0,'allocated_gpu_seconds':1080,'deadline_epoch':1080,'setup_deadline_epoch':360}
            self.assertEqual(W.assignment_check(a,request,now=10,pod_id='own'),900)
            for k,v in [('allocated_gpu_seconds',1081),('previous_gpu_seconds',1),('separate_pod_verified',False),('setup_deadline_epoch',361),('deadline_epoch',1081)]:
                with self.subTest(field=k),self.assertRaises(ValueError):W.assignment_check({**a,k:v},request,now=10,pod_id='own')

    def test_archive_extra_private_file_rejected(self):
        import tarfile,io
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.tar.gz'
            with tarfile.open(p,'w:gz') as t:
                info=tarfile.TarInfo('labels.PRIVATE.json');info.size=2;t.addfile(info,io.BytesIO(b'{}'))
            with self.assertRaises(ValueError):archive_members(p)


if __name__=='__main__':unittest.main()
