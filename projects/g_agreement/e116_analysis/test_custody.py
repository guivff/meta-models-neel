import unittest
from unittest.mock import patch
from pathlib import Path
from . import adapter as a
class CustodyTests(unittest.TestCase):
    def test_original_binding_and_root_restored(self):
        b={'inventory_seal':'/tmp/source/inventory/seal.json'};old=a.original.ROOT
        def check(got):
            self.assertIs(got,b);self.assertEqual(a.original.ROOT,Path('/tmp/source').resolve());return [],{}
        with patch.object(a.subprocess,'check_output',return_value='/tmp/source\n'),patch.object(a.original,'inputs',side_effect=check):
            self.assertEqual(a.original_inputs(b),([],{}))
        self.assertEqual(a.original.ROOT,old)
    def test_failure_restores_root(self):
        old=a.original.ROOT
        with patch.object(a.subprocess,'check_output',return_value='/tmp/source\n'),patch.object(a.original,'inputs',side_effect=ValueError('invalid')):
            with self.assertRaises(ValueError):a.original_inputs({'inventory_seal':'/tmp/source/seal.json'})
        self.assertEqual(a.original.ROOT,old)
