import pytest
from projects.g_agreement.core.analysis_utils import parse_target_answer
from .classifier import classify,pair_preference


def raw(text,**kw):return dict(text=text,token_ids=[1,2],greedy_max_new_tokens=3,**kw)


@pytest.mark.parametrize('text,expected',[('PARIS.','old'),('London','new'),('Paris London','other'),('neither','other'),('','other'),('Parisian','other'),('(London)!','new'),('New York','new')])
def test_exact_existing_matcher(text,expected):
    candidates=dict(old='Paris',new='New York'if text=='New York'else 'London')
    item={'primary':{'candidates':list(candidates.values()),'answer':candidates['old']}}
    actual=parse_target_answer(item,text)
    assert classify(raw(text),candidates)==expected
    assert expected==next((k for k,v in candidates.items()if actual==v),'other')


def test_missing_distinct_from_neither_and_no_aliases():
    c=dict(old='United States',new='United Kingdom')
    assert classify(None,c)is None
    assert classify(raw('USA'),c)=='other'
    assert classify(raw('United States and United Kingdom'),c)=='other'


def test_logit_preference_cannot_override_greedy():
    r=raw('Paris',pair_logits=[[1,8],[2,5]])
    assert classify(r,dict(old='Paris',new='London'))=='old'
    assert pair_preference(r,'B')is True
    assert pair_preference(raw('London',pair_logits=[[3,3]]),'B')is False
    assert pair_preference(raw('London'),'B')is None


@pytest.mark.parametrize('change',[dict(greedy_max_new_tokens=4),dict(token_ids=[1,2,3,4])])
def test_registered_acquisition_only(change):
    r=raw('London');r.update(change)
    with pytest.raises(ValueError):classify(r,dict(old='Paris',new='London'))
