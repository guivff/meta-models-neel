"""Synthetic activation bytes test input binding, not E39 scientific execution."""
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
import contract as C
import prepare_inputs as P
import package as K


class CaptureBinding(unittest.TestCase):
    def test_verified_capture_conversion_and_private_labels_not_staged(self):
        stage=C.ROOT/'cache/g_agreement/understand/e39-stage-v1'
        items=C.rows(stage/'source.items.audit.jsonl')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'cache';pull=root/'synthetic_capture';pull.mkdir(parents=True)
            C.dump(pull/'runtime.json',{'status':'COMPLETE','plan_sha256':'synthetic'})
            C.dump(pull/'plan.json',{'plan_sha256':'synthetic','freeze':{'sha256':P.FREEZE_HASH},'candidates':{'sha256':P.CANDIDATES_HASH}})
            C.dump(pull/'environment.json',{'synthetic':True})
            C.dump(pull/'items.order.json',[r['id'] for r in items])
            np.save(pull/'acts44.npy',np.ones((len(items),5120),dtype='float32'),allow_pickle=False)
            C.dump(pull/'capture.audit.json',{'blocks':[42,44],'padding_side':'right','items':[{'id':r['id'],'feature':r['feature'],'length':r['source_length'],'padding_tokens':0} for r in items]})
            C.seal(pull,'OUTPUT_SEAL.json');seal=C.read(pull/'OUTPUT_SEAL.json');seal.update(experiment='E36',plan_sha256='synthetic');C.dump(pull/'OUTPUT_SEAL.json',seal)
            out=root/'input';result=P.prepare(stage,[pull],out)
            self.assertEqual(result['status'],'COMPLETE')
            self.assertEqual(np.load(out/'test.acts44.npy').shape,(1512,5120))
            worker=root/'worker';worker.mkdir()
            for n in [*C.read(out/'INPUT_SEAL.json')['files'],'INPUT_SEAL.json']:shutil.copyfile(out/n,worker/n)
            C.worker_input(worker)
            with self.assertRaises(ValueError):C.worker_input(out) # private key/receipt prohibited
            K.archive(root/'input.tar.gz',{n:worker/n for n in [*C.read(worker/'INPUT_SEAL.json')['files'],'INPUT_SEAL.json']})
            import tarfile
            with tarfile.open(root/'input.tar.gz') as t:self.assertFalse(any('DO_NOT_STAGE' in n for n in t.getnames()))
            with self.assertRaisesRegex(ValueError,'duplicate'):
                P.prepare(stage,[pull,pull],root/'duplicate')
            # A failed E36 pull cannot become a valid training input, even with a fresh seal.
            C.dump(pull/'runtime.json',{'status':'PARITY_FAILED','plan_sha256':'synthetic'})
            seal['files']['runtime.json']=C.sha(pull/'runtime.json');C.dump(pull/'OUTPUT_SEAL.json',seal)
            with self.assertRaisesRegex(ValueError,'complete verified'):
                P.prepare(stage,[pull],root/'bad')


if __name__=='__main__':unittest.main()
