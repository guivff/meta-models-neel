import json,unittest
from state84 import test_results,scan,hidden,readonly_shell

def call(name,args):return dict(role='assistant',content='',tool_calls=[dict(function=dict(name=name,arguments=json.dumps(args)))])
def tool(s):return dict(role='tool',content=s,tool_calls=None)
class Tests(unittest.TestCase):
 def test_pytest(self):
  self.assertEqual(test_results('python -m pytest -q','=== 3 passed in 0.4s ==='),[1]);self.assertEqual(test_results('cd /repo && pytest tests','=== 1 failed, 3 passed in 0.4s ==='),[0]);self.assertEqual(test_results('pytest','no useful result'),[])
  self.assertIsNone(test_results('cat tests.py','=== 3 passed in 0.4s ==='));self.assertEqual(test_results('cat notes && pytest','1 failed in 0.1s'),[0])
 def test_unittest(self):
  self.assertEqual(test_results('python -m unittest','Ran 4 tests in 0.1s\n\nOK\n'),[1]);self.assertEqual(test_results('python -m unittest','Ran 4 tests in 0.1s\n\nFAILED (failures=1)\n'),[0])
 def test_pre_assistant_only_and_count_bins(self):
  msgs=[]
  for n in range(3):msgs.extend([call('execute_bash',dict(command='pytest -q')),tool('1 failed in 0.1s')])
  msgs.append(dict(role='assistant',content='later future answer',tool_calls=None));s=list(scan(msgs))
  self.assertEqual(s[0]['labels'],{});self.assertEqual(s[1]['labels']['failed_attempts'],0);self.assertNotIn('failed_attempts',s[2]['labels']);self.assertEqual(s[-1]['labels']['failed_attempts'],1);self.assertEqual(s[-1]['labels']['last_test_passed'],0)
 def test_two_file_ordinal_and_failed_edit(self):
  msgs=[call('str_replace_editor',dict(command='create',path='/a.py')),tool('File created successfully'),call('str_replace_editor',dict(command='create',path='/b.py')),tool('File created successfully'),call('str_replace_editor',dict(command='str_replace',path='/a.py')),tool('The file has been edited\n1 def code():\n2     raise Error("does not exist")'),call('str_replace_editor',dict(command='str_replace',path='/c.py')),tool('Error: old_str not found'),dict(role='assistant',content='',tool_calls=None)]
  s=list(scan(msgs));self.assertEqual(s[-1]['files'],['/a.py','/b.py']);self.assertEqual(s[-1]['labels']['file_being_edited'],0)
 def test_unknown_write_and_unknown_test(self):
  msgs=[call('execute_bash',dict(command='pytest')),tool('unclear'),call('execute_bash',dict(command='pytest')),tool('1 failed in 0.1s'),dict(role='assistant',content='',tool_calls=None)]
  s=list(scan(msgs))[-1];self.assertNotIn('failed_attempts',s['labels']);self.assertEqual(s['labels']['last_test_passed'],0)
 def test_shell_history_certainty(self):
  for command in ['cd /repo && cat a.py | head -20','sed -n \"1,100p\" a.py','git diff -- a.py','find /repo -name a.py']:
   self.assertTrue(readonly_shell(command),command)
  for command in ['sed -i \"s/a/b/\" a.py','python -c \"print(1)\"','git reset --hard','find /repo -delete','echo x > a.py','cat $(makefile)']:
   self.assertFalse(readonly_shell(command),command)
 def test_hidden_tail(self):
  self.assertFalse(hidden('last_test_passed','3 passed',[]));self.assertTrue(hidden('last_test_passed','[Command finished with exit code 0]',[]));self.assertFalse(hidden('failed_attempts','third attempt',[]));self.assertFalse(hidden('file_being_edited','Read a.py',['/src/a.py','/src/b.py']));self.assertTrue(hidden('file_being_edited','def function(): return 2',['/src/a.py','/src/b.py']))
if __name__=='__main__':unittest.main()

class QuotedShellTests(unittest.TestCase):
 def test_quoted_arguments_are_not_shell_operators(self):
  for command in ['find /repo -name "a|b.py" | xargs grep -n "value;field"','grep "a && b" a.py | sort | uniq -c','sed -n "1,10p" a.py 2>/dev/null','ls\ncat a.py']:
   self.assertTrue(readonly_shell(command),command)
 def test_mutating_flags_remain_unknown(self):
  for command in ['sort -o a.py b.py','find /repo -fprint a.py','xargs rm','sed -n "1,10p" -i a.py','ls\nrm a.py','echo x >| a.py']:
   self.assertFalse(readonly_shell(command),command)
