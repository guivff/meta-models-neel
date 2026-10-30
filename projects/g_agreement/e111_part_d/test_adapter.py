import numpy as np
from .adapter import source_features,split_report
from .test_analysis import rows
import pytest


def test_natural_baseline_not_random_pair():
    m=dict(natural=[1.,2.],vector_parameters=dict(vector=[4.,6.]),target_class=1)
    f=source_features(m,dict(vector_mode='persisted'),lambda x:x,[2.,0.])
    assert f['displacement_norm']==5 and f['probe_logit_shift']==6


def test_separate_conditions_do_not_pool():
    xs=rows()
    for x in xs:x['condition']='steered'
    random=[dict(x,id=x['id']+'random',condition='random',y=1-x['y']) for x in xs]
    z=split_report(xs+random)
    assert z['primary']['rows']['synthetic']['probe_logit_shift']['overlap_weighted_gap']==1
    assert z['random_direction_reference']['rows']['synthetic']['probe_logit_shift']['overlap_weighted_gap']==-1


def test_unknown_condition_rejected():
    with pytest.raises(ValueError):split_report([dict(x,condition='guessed') for x in rows()])


def test_missing_condition_group_explicit():
    z=split_report([dict(x,condition='steered') for x in rows()])
    assert z['random_direction_reference']['status']=='NOT AVAILABLE'
