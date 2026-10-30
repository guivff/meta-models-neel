import unittest
import numpy as np

class Gate(unittest.TestCase):
 def test_strict_gate_silence_and_denominator(self):
  from metrics_b import gate_counts
  a=gate_counts([1,0,1],[1,1,0],[.2,.5,.9],[.5,.1]).sum(0)
  np.testing.assert_array_equal(a,[[3,2,1],[3,0,0],[3,2,1]])
