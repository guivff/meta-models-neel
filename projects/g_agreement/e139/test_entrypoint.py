import unittest
from unittest.mock import patch
from pathlib import Path
from . import run_after_complete as r
class Tests(unittest.TestCase):
 def test_fixed_cpu_binding_output_and_guard(self):
  with patch.object(r,'run')as run:
   r.main(['--acquisition-root','/SEALED','--acquisition-sha','a'*64])
   run.assert_called_once_with(r.CPU_ROOT,r.CPU_SHA,Path('/SEALED'),'a'*64,r.OUT,r.GUARD)
 def test_unsealed_placeholder_refused_before_execution(self):
  with patch.object(r,'run')as run,patch('sys.stderr'):
   with self.assertRaises(SystemExit):r.main(['--acquisition-root','/SEALED','--acquisition-sha','PENDING'])
   run.assert_not_called()
if __name__=='__main__':unittest.main()
