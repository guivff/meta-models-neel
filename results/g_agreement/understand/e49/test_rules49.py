import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rules49 import evaluate

def metric(kind,oracle,**kw):return dict(kind=kind,oracle=oracle,bow=.5,probe=.9,base=.85,**kw)

def test_registered_thresholds_and_middle_band():
 rows={'asserted_vs_hypothetical':metric('semantic_state',.65),'topic_twin':metric('descriptor',.80),'decimal_separator':metric('surface_state',.72)}
 r=evaluate(rows,{'asserted_vs_hypothetical':'UNSAYABLE','topic_twin':'SAYABLE','decimal_separator':'SAYABLE'})
 assert all(r[x]['status']=='HOLDS' for x in ['R1','R2','R3'])
 assert r['precall_accuracy']['accuracy']==2/3
 assert r['precall_accuracy']['role']=='primary'
 assert r['precall_accuracy_middle_band_excluded']['accuracy']==1.
 assert r['precall_accuracy_middle_band_excluded']['n']==2
 assert r['precall_accuracy_middle_band_excluded']['excluded_middle_band_rows']==['decimal_separator']
 assert r['semantic_state_n']==1 and r['falsifier']['status']=='NOT MET'

def test_failed_gate_not_counted_and_missing_group_unevaluable():
 rows={'s':metric('semantic_state',.5),'d':metric('descriptor',.9)}
 rows['s']['bow']=.650001
 r=evaluate(rows,{'s':'UNSAYABLE','d':'SAYABLE'})
 assert r['excluded_rows']=={'s':['BOW > 0.65']}
 assert r['R1']['status']==r['R2']['status']==r['falsifier']['status']=='NOT EVALUABLE'

def test_descriptor_bow_exempt_but_probe_gate_required():
 rows={'d':metric('descriptor',.9)};rows['d']['bow']=1.
 assert evaluate(rows,{'d':'SAYABLE'})['gated_rows']==['d']
 rows['d']['probe']=.899
 assert evaluate(rows,{'d':'SAYABLE'})['gated_rows']==[]

def test_falsifier_half_of_gated_semantic_states():
 rows={'a':metric('semantic_state',.8),'b':metric('semantic_state',.5)}
 r=evaluate(rows,{'a':'UNSAYABLE','b':'UNSAYABLE'})
 assert r['falsifier']['status']=='HOLDS'
 assert r['precall_accuracy']['accuracy']==.5

def test_both_accuracy_denominators_exclude_failed_gates():
 rows={'low':metric('semantic_state',.65),'high':metric('descriptor',.80),'middle':metric('surface_state',.70),'failed':metric('descriptor',.90)}
 rows['failed']['probe']=.89
 r=evaluate(rows,{'low':'UNSAYABLE','high':'UNSAYABLE','middle':'SAYABLE'})
 assert r['precall_accuracy']['n']==3
 assert r['precall_accuracy']['accuracy']==1/3
 d=r['precall_accuracy_middle_band_excluded']
 assert d['role']=='descriptive' and d['n']==2 and d['accuracy']==.5
 assert set(d['correct_by_row'])=={'low','high'}

def test_descriptive_empty_denominator_is_not_zero_accuracy():
 r=evaluate({'middle':metric('surface_state',.70)},{'middle':'UNSAYABLE'})
 assert r['precall_accuracy']['accuracy']==0.
 assert r['precall_accuracy_middle_band_excluded']['n']==0
 assert r['precall_accuracy_middle_band_excluded']['accuracy'] is None

def test_failed_row_reader_score_is_never_accessed():
 class UnreadReader(dict):
  def __getitem__(self,key):
   if key=='oracle':raise AssertionError('reader score accessed before qualification')
   return super().__getitem__(key)
 failed=UnreadReader(kind='semantic_state',bow=.5,base=.85,probe=.89)
 r=evaluate({'failed':failed},{})
 assert r['gated_rows']==[] and r['precall_accuracy']['n']==0
