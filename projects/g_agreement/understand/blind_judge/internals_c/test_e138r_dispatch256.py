import ast,subprocess,unittest
from unittest.mock import patch
from . import e138r_dispatch256 as m
class Tests(unittest.TestCase):
 def test_missing_actual_human_approval_blocks_activation(self):
  with patch.object(m,'read',return_value={}):
   with self.assertRaises(Exception):m.activate()
 def test_exact_current_audit_function_unchanged(self):
  old=subprocess.check_output(['git','show','189b162ee:'+m.OPS],cwd=m.ROOT).decode();now=(m.ROOT/m.OPS).read_text()
  def f(s):return ast.dump(next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)and n.name=='audit_response'),include_attributes=False)
  self.assertEqual(f(old),f(now))
 def test_wire_and_values_still_original_reviewed_renderer(self):
  from .e138r_channel254 import render
  self.assertIs(m.render,render)
