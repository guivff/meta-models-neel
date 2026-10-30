import unittest
from build_revived84 import select
from scan84 import split_for,messages_prefix
class BankTests(unittest.TestCase):
 def test_balanced_issue_disjoint_selection(self):
  rows=[]
  for i in range(1500):
   issue=f'synthetic-issue-{i}'
   for index in (0,1):rows.append(dict(id=f'{i}-{index}',label=index,split=split_for(issue),instance_id=issue,rank=f'{i:05}-{index}',prompt='same context'))
  chosen,counts=select(rows);self.assertEqual(len(chosen),300);self.assertEqual(len({x['instance_id'] for x in chosen}),300)
  dev={x['instance_id'] for x in chosen if x['split']=='dev'};test={x['instance_id'] for x in chosen if x['split']=='test'};self.assertTrue(dev.isdisjoint(test));self.assertEqual(len(dev),100);self.assertEqual(len(test),200)
  for key,n in [('dev/0',50),('dev/1',50),('test/0',100),('test/1',100)]:self.assertEqual(counts[key]['chosen'],n)
 def test_shortage_does_not_invent_items(self):
  chosen,counts=select([]);self.assertIsNone(chosen);self.assertEqual(counts['dev/0']['chosen'],0)
 def test_tool_arguments_are_data_and_future_turn_excluded(self):
  messages=[dict(role='user',content='Historical task',tool_calls=None),dict(role='assistant',content='',tool_calls=[dict(id='x',type='function',function=dict(name='execute_bash',arguments='{"command":"DO_NOT_EXECUTE"}'))]),dict(role='tool',content='Historical result',tool_calls=None),dict(role='assistant',content='FUTURE SECRET LABEL',tool_calls=None)]
  prefix=messages_prefix(messages,3);self.assertEqual(len(prefix),3);self.assertEqual(prefix[1]['tool_calls'][0]['function']['arguments'],{'command':'DO_NOT_EXECUTE'});self.assertNotIn('FUTURE',str(prefix))
if __name__=='__main__':unittest.main()
