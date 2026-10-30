import hashlib
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from . import ops, pull_capture as p


class PullTests(unittest.TestCase):
    def test_synthetic_pull_verifies_all_shards_and_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); payload=b'synthetic'
            seal={'status':'CAPTURE_COMPLETE','n':14184,'input_seal_sha256':p.resident.PORT_SHA,
                  'sealed_at':ops.utc(),'files':{'0000.tar':hashlib.sha256(payload).hexdigest()}}
            raw=ops.encoded(seal); calls=[]
            def fake(host,remote,name,target,end):
                calls.append(name);target.write_bytes(raw if name=='SEAL.json' else payload)
            p.pull('synthetic','/synthetic',hashlib.sha256(raw).hexdigest(),root/'pull',time.time()+300,fake)
            self.assertEqual(set(calls),{'SEAL.json','0000.tar'})
            self.assertTrue((root/'pull/PULL_RECEIPT.json').exists())
    def test_no_window_reset_or_shell_injection(self):
        with tempfile.TemporaryDirectory() as td:
            seal={'status':'CAPTURE_COMPLETE','n':14184,'input_seal_sha256':p.resident.PORT_SHA,'sealed_at':ops.utc(),'files':{'0000.tar':'a'*64}}
            raw=ops.encoded(seal)
            def fake(host,remote,name,target,end):target.write_bytes(raw)
            with self.assertRaises(ValueError):p.pull('x','/x',hashlib.sha256(raw).hexdigest(),Path(td)/'pull',time.time()+700,fake)
            with patch.object(p.subprocess,'run') as call:
                for host,remote in [('x;echo','/x'),('x','/x;echo'),('x','/../x')]:
                    with self.assertRaises(ValueError):p.copy_one(host,remote,'0000.tar',Path(td)/'a',time.time()+10)
                call.assert_not_called()


if __name__=='__main__':unittest.main()
