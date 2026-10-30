from projects.g_agreement.ops.i5_e98_analysis_bridge import count_objects,old_rubric_sensitivity
import pytest

def test_count_objects_exact():assert count_objects({'x':{'distinct_count':2}})=={'x':{'id':'x','measurement':{'distinct_count':2}}}
def test_no_old_subset_replacement():
 with pytest.raises(ValueError):old_rubric_sensitivity([],{},[],{})
def test_duplicate_old_ids_rejected():
 with pytest.raises(ValueError):old_rubric_sensitivity([],{},[{'id':'x'}]*447,{})

def test_matched_subset_uses_frozen_signed_kernel():
 from projects.g_agreement.ops.i5_e98_analysis_bridge import old_rubric_sensitivity
 ids=[str(i)for i in range(448)];units=[dict(bank='E57',row='synthetic',binary=True,items=[dict(id=i,label=1)for i in ids])]
 def code(i,v):return dict(id=i,category='states_value',values=[v],evidence='token')
 primary={i:code(i,'A')for i in ids};old=[code(i,'B')for i in ids[:447]];native={i:'token'for i in ids}
 r=old_rubric_sensitivity(units,primary,old,native)
 assert r['items']==r['rows'][0]['sampled_items']==447 and r['category_equal']==447 and r['value_set_equal']==0
 assert r['rows'][0]['amended_matched']['S']==1 and r['rows'][0]['original_matched']['S']==-1
