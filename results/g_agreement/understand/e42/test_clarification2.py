import unittest
from unittest.mock import patch
import run42
class ExclusionTests(unittest.TestCase):
 def test_disagree_is_excluded_without_continuation_evaluation(self):
  item={'ids':[1],'value':'inside'}
  with patch.object(run42,'state',return_value='outside'),patch.object(run42,'persistence',side_effect=AssertionError('continuation accessed')):
   self.assertEqual(run42.classified_persistence(item,None,lambda ids:'prefix'),(None,'disagree'))
 def test_undetermined_is_excluded(self):
  with patch.object(run42,'state',return_value=None):
   self.assertEqual(run42.classified_persistence({'ids':[1],'value':'inside'},None,str),(None,'undetermined'))
 def test_agreement_uses_unchanged_core(self):
  with patch.object(run42,'state',return_value='inside'),patch.object(run42,'persistence',return_value=5) as core:
   self.assertEqual(run42.classified_persistence({'ids':[1],'value':'inside'},[2]*32,str),(5,'agree'));core.assert_called_once()
