import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('e74_deployment_verifier',HERE/'verify_deployment.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


class DeploymentTests(unittest.TestCase):
    def test_full_runtime_closure_and_author_pins(self):
        entries=v.lock(HERE/'runtime.lock')
        self.assertEqual(len(entries),209)
        self.assertTrue(all(entries[k]['version']==value for k,value in v.CORE.items()))
        self.assertEqual(len(v.lock(HERE/'build.lock')),6)
        self.assertEqual(v.lock(HERE/'fork.lock')['vllm-lens']['hashes'],[v.WHEEL_SHA])
    def test_unpinned_missing_hash_or_duplicate_lock_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'lock'
            for value in ['pkg>=1\n','pkg==1\n','pkg==1\n    --hash=sha256:'+'a'*64+'\npkg==1\n']:
                p.write_text(value)
                with self.assertRaises(ValueError):v.lock(p)
    def test_installation_check_rejects_wrong_target_before_package_import(self):
        with patch.object(v.platform,'system',return_value='Darwin'),patch.object(v.subprocess,'run') as run:
            with self.assertRaises(ValueError):v.installed(HERE)
            run.assert_not_called()
    def test_tampered_locked_input_rejected_before_wheel_use(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'runtime.lock').write_text('tampered')
            (root/'RECIPE.json').write_text(json.dumps({'locked_inputs':{'runtime.lock':'a'*64}}))
            with self.assertRaises(ValueError):v.artifacts(root,root/'missing.whl')
    def test_tampered_author_tar_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'author.tar.gz';p.write_bytes(b'synthetic-invalid-source')
            with self.assertRaises(ValueError):v.sources(p)


if __name__=='__main__':unittest.main()
