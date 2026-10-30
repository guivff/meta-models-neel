import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from diagnostics import row_diagnostics

def test_gate_margin_and_nearest_vectors():
 variants=['A']*3+['B']*3;arms=['full','J','nonJ']*2;v=np.array([[1.,0]]*3+[[-1.,0]]*3);test=np.array([[1.,0],[-1.,0]])
 d=row_diagnostics([1,1,.9,-1,-1,-.9],v,variants,arms,test)
 assert d['eligible'] and d['probe_margin_ratio_nonJ_over_J']==.9 and all(x['distance']==0 for x in d['nearest_real_test'])
 d=row_diagnostics([1,1,.7,-1,-1,-.7],v,variants,arms,test);assert not d['eligible']
 v[2]=[0.,1.];d=row_diagnostics([1,1,1,-1,-1,-1],v,variants,arms,test);assert not d['eligible'] and d['arm_distance_difference_by_class']['A']==1
