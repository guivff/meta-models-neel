import pytest
from .deviation2 import score, GUARD
from .adapter import GUARD as ORIGINAL_GUARD
from .analysis import summarize, readings
from .test_analysis import rows

def test_code_source_ignores_bullet_register():
    assert score({'a': True}) is True
    assert score({'a': False}) is False

def test_unparseable_remains_missing():
    assert score({'a': None}) is None

@pytest.mark.parametrize('bad', [0, 1, 'yes', 'UNPARSEABLE'])
def test_no_coercion(bad):
    with pytest.raises(ValueError): score({'a': bad})

def test_distinct_guard():
    assert GUARD != ORIGINAL_GUARD
    assert GUARD.name == 'DEVIATION2_ONCE.json'

def test_thresholds_and_missingness_unchanged():
    xs=rows()
    assert readings(summarize(xs))['targeted_reading']=='reporting-priority failure'
    xs[0]['yes']=None
    assert readings(summarize(xs))['targeted_reading']=='NOT EVALUABLE'
