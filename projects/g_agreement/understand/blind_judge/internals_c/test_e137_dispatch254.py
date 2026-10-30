import ast,subprocess,unittest
from unittest.mock import patch
from .e137_dispatch254 import terminal_record,OPS
from .e137_channel253 import render
from .transport import decode,ROOT
class Tests(unittest.TestCase):
 def test_actual_decode_envelope_not_validator_return(self):
  import json
  u=dict(id='0'*32,property='p',values={'A':['a'],'B':['b']},readout='a');call,validator=render('E137',u)
  record=dict(id=u['id'],category='states_value',values=['A'],evidence='a')
  saved=dict(response=dict(usage=dict(cost=0.001),choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(records=[record]))))]))
  with patch('projects.g_agreement.understand.blind_judge.internals_c.transport.audit_response',return_value={}):t,_=decode(call,saved,None,validator)
  self.assertEqual(terminal_record(t),record);self.assertEqual(set(t['result']),{'records'})
 def test_missing_remains_null(self):self.assertIsNone(terminal_record(dict(status='UNPARSEABLE',result=None)))
 def test_actual_audit_function_unchanged(self):
  old=subprocess.check_output(['git','show','ba71e2844:'+OPS],cwd=ROOT).decode();now=(ROOT/OPS).read_text()
  def f(s):return ast.dump(next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)and n.name=='audit_response'),include_attributes=False)
  self.assertEqual(f(old),f(now))
