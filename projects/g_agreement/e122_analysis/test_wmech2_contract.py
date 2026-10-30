"""Independent W-mech2 synthetic checks for direct §232 request; no real scores."""
import pytest
from . import rules

ORDER=['hedge','self','stop','formal']

def native(n,split,shifts):
    return [dict(id=f'{split}-{q}-{g}-{a}',quartet_id=f'{q:03}',genre=g,addressed=a,split=split,scores={k:a*v for k,v in shifts.items()}) for q in range(n) for g in (0,1) for a in (0,1)]

def test_signed_dev_selection_not_absolute_or_test():
    choice=rules.select_dev(native(50,'dev',dict(zip(ORDER,[-5,2,1,0]))),ORDER)
    assert choice['selected_contrast_id']=='self'
    with pytest.raises(ValueError):rules.select_dev(native(50,'test',dict(zip(ORDER,[1,2,3,4]))),ORDER)

def test_frozen_order_tie_and_complete_quartets():
    xs=native(50,'dev',dict.fromkeys(ORDER,1))
    assert rules.select_dev(xs,ORDER)['selected_contrast_id']==ORDER[0]
    with pytest.raises(ValueError):rules.select_dev(xs[:-1],ORDER)

def test_native_gate_and_bootstrap_reuse():
    result=rules.native_test(native(100,'test',{'self':2}), 'self')
    assert result['R_BEV1']=='MET'
    assert result['native_addressed_shift']==rules.statistic([2]*100)
    assert rules.native_test(native(100,'test',{'self':0}),'self')['transplant_disposition']=='NOT RUN'

def test_transplant_fraction_not_clipped():
    gate=rules.native_test(native(100,'test',{'self':2}), 'self')
    xs=[dict(id=f'{q}-{g}',quartet_id=f'{q:03}',genre=g,addressed=0,split='test',scores=dict(T=4,S=1)) for q in range(100) for g in (0,1)]
    result=rules.transplant(xs,gate)
    assert result['R_BEV2']=='MET' and result['delta']['estimate']==3
    assert result['fraction_recovered']['estimate']==1.5 and result['fraction_recovered']['clipped'] is False
    gate['R_BEV1']='NOT MET'
    with pytest.raises(ValueError):rules.transplant(xs,gate)

def test_pair_genres_before_bootstrap():
    xs=native(100,'test',{'self':0})
    for x in xs:x['scores']['self']=x['addressed']*(3 if x['genre']==0 else -1)
    result=rules.native_test(xs,'self')
    assert result['native_addressed_shift']==rules.statistic([1]*100)
