import unittest
import e82_dispatch as D
class Tests(unittest.TestCase):
 def group(self):return dict(id='opaque',rubric='frozen',positions=[dict(position=0,readout='The value is “alpha”.'),dict(position=1,readout='other native')])
 def code(self,**kw):
  x=dict(id='opaque',category='states_value',values=['A'],evidence='The value is "alpha".');x.update(kw);return x
 def classify(self,codes,allowed=['A','B']):return D.classify([self.group()],dict(records=codes),{'opaque':allowed})[0]
 def test_frozen_normalization_kept(self):self.assertEqual(self.classify([self.code()])['status'],'KEPT')
 def test_missing_truth_never_accepts_B(self):self.assertEqual(self.classify([self.code(values=['B'])],['A'])['status'],'INVALID')
 def test_duplicate_id_invalid(self):self.assertEqual(self.classify([self.code(),self.code()])['status'],'INVALID')
 def test_position_headers_not_evidence(self):self.assertEqual(self.classify([self.code(evidence='position')])['status'],'INVALID')
 def test_cross_position_evidence_invalid(self):self.assertEqual(self.classify([self.code(evidence='alpha”. other native')])['status'],'INVALID')
 def test_silent_with_empty_evidence_kept(self):self.assertEqual(self.classify([self.code(category='silent',values=[],evidence='')])['status'],'KEPT')
if __name__=='__main__':unittest.main()
