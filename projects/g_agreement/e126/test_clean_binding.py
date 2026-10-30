import copy
import pytest
from projects.g_agreement.e126.bind_clean import match_inputs


def sample():
    t=[dict(id='target1',row='fact_recall',ids=[1,2],read_index=1,candidate_ids=[[[3],[4]]]),
       dict(id='target2',row='language_plan',ids=[2,3],read_index=1,candidate_ids=[[[4],[5]],[[6],[5]]])]
    s=[dict(x,id='other-experiment-'+x['id'],condition='0',vector_index=None,donor_id=None,inventory_id='inventory-'+x['id'])for x in t]
    return t,s


def test_different_ids_match_only_exact_original_input_not_order():
    t,s=sample();before=copy.deepcopy((t,s));matched=match_inputs(t,list(reversed(s)))
    assert [b['id']for a,b in matched]==[s[0]['id'],s[1]['id']]
    assert (t,s)==before


def test_duplicate_input_is_refused_not_arbitrarily_selected():
    t,s=sample()
    with pytest.raises(ValueError,match='ambiguous'):match_inputs(t,s+[dict(s[0],id='duplicate')])


@pytest.mark.parametrize('field,value',[('ids',[1,9]),('read_index',0),('candidate_ids',[[[4],[3]]]),('row','different')])
def test_prompt_read_index_pair_orientation_or_row_change_refused(field,value):
    t,s=sample();s[0][field]=value
    with pytest.raises(ValueError,match='no exact'):match_inputs(t,s)


@pytest.mark.parametrize('field,value',[('condition','S'),('vector_index',0),('donor_id','donor')])
def test_random_or_steered_sources_cannot_be_clean(field,value):
    t,s=sample();s[0][field]=value
    with pytest.raises(ValueError,match='unpatched'):match_inputs(t,s)
