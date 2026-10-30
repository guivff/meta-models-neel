"""Security regression checks in disposable repositories; no real private data used."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[4]
HOOK=ROOT/'.githooks/pre-commit'


def check_file(name,content):
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        subprocess.run(['git','init','-q',str(root)],check=True,capture_output=True)
        file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(content)
        subprocess.run(['git','-C',str(root),'add','--',name],check=True,capture_output=True)
        return subprocess.run(['python3',str(HOOK)],cwd=root,capture_output=True,text=True)


class CustodyHookTests(unittest.TestCase):
    def test_later_deletion_does_not_hide_private_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            subprocess.run(['git','init','-q',str(root)],check=True,capture_output=True)
            (root/'dummy.PRIVATE.json').write_text('{}')
            subprocess.run(['git','-C',str(root),'add','dummy.PRIVATE.json'],check=True,capture_output=True)
            subprocess.run(['git','-C',str(root),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','synthetic history fixture'],check=True,capture_output=True)
            subprocess.run(['git','-C',str(root),'rm','dummy.PRIVATE.json'],check=True,capture_output=True)
            result=subprocess.run(['python3',str(HOOK)],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertIn('reachable history',result.stderr)

    def test_private_filename_rejected_even_without_secrets(self):
        result=check_file('nested/pairing.PRIVATE.json',b'{}')
        self.assertEqual(result.returncode,1)
        self.assertIn('private filename in index',result.stderr)

    def test_case_variant_also_rejected(self):
        result=check_file('nested/PAIRING.private.json',b'{}')
        self.assertEqual(result.returncode,1)

    def test_credential_block_does_not_echo_value(self):
        value=('h'+'f_'+'x'*24).encode()
        result=check_file('normal.txt',value)
        self.assertEqual(result.returncode,1)
        self.assertNotIn(value.decode(),result.stdout+result.stderr)

    def test_public_hashes_and_ordinary_offline_identifiers_pass(self):
        result=check_file('public.json',b'{"hash":"0123456789abcdef","offline":"HF_HUB_OFFLINE","cache_arg":"hf_home"}')
        self.assertEqual(result.returncode,0)
        self.assertIn('0 private paths; 0 credential findings',result.stdout)


if __name__=='__main__':unittest.main()
