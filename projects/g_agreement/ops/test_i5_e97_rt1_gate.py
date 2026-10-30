import importlib.util
import pytest
from projects.g_agreement.ops import i5_e97_rt1_gate as g
def fixture():
 return {k:[dict(row=str(i),S=.3 if i<20 else 0,CI95=[.1,.5] if i<20 else [-.1,.1],reported=i<20,j_label='IN-J' if i%2 else 'DIFFUSE',j_reported=bool(i%2),taxonomy='continuation constraint') for i in range(40)] for k in ['oracle','nla']}
def test_complete_two_readers():assert g.validate_units(fixture())
def test_missing_never_missed():
 x=fixture();x['oracle'][0]['S']=None
 with pytest.raises(ValueError):g.validate_units(x)
def test_truth_and_forecast_frozen():
 x=fixture();x['oracle'][0]['reported']=False
 with pytest.raises(ValueError):g.validate_units(x)
 x=fixture();x['oracle'][0]['j_reported']=True
 with pytest.raises(ValueError):g.validate_units(x)
def test_full_grid():
 x=fixture();x['nla'].pop()
 with pytest.raises(ValueError):g.validate_units(x)
def test_terminal_gate():
 d=dict(status='VERIFIED_COMPLETE_E97_JUDGMENTS',primary_records=6668,old_rubric_records=1667,native_records=6720,all_member_hashes_verified=True,route_privacy_verified=True)
 g.validate_terminal(d);d['primary_records']=99
 with pytest.raises(ValueError):g.validate_terminal(d)
