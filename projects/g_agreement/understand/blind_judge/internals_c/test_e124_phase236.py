import pytest
from .e124_phase236 import census_scope


def test_no_truth_custody_preserved_without_extra_calls_and_future_sources_fixed():
    a=dict(id='a',classification=dict(seal_index=5),context_terminal=dict(seal_index=7),model_terminal=dict(seal_index=8))
    b=dict(id='b',classification=dict(seal_index=5),disposition='EXCLUDED_BY_REGISTERED_SOURCE_COHORT_NO_JUDGMENT')
    census_scope([a,b],['a'],n=2)
    with pytest.raises(ValueError):census_scope([a,b],['a','b'],n=2)
    with pytest.raises(ValueError):census_scope([a,a],['a'],n=2)
    a['context_terminal']['seal_index']=8
    with pytest.raises(ValueError):census_scope([a,b],['a'],n=2)
