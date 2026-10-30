import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from . import e133_channel245 as new,e133_channel as original,registered,transport
class FrozenWrapperTest(unittest.TestCase):
 def test_separate_profile_without_editing_original(self):
  prior=registered.HERE
  with patch.object(original,'source_gate'):
   with new.worker():self.assertEqual(registered.HERE,transport.HERE/'E133245')
  self.assertEqual(registered.HERE,prior)
 def test_once_guard_prevents_second_dispatch(self):
  with tempfile.TemporaryDirectory()as d,patch.object(new,'source_gate',return_value=Path(d)/'source'):
   (Path(d)/'source').write_text('x');new.once(d)
   with self.assertRaises(FileExistsError):new.once(d)
if __name__=='__main__':unittest.main()
