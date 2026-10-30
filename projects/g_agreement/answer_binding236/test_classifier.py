import pytest
from projects.g_agreement.core.analysis_utils import parse_target_answer
from projects.g_agreement.e101.bind_owner import PAIRS
from . import classifier as C


@pytest.mark.parametrize('text,want', [('Paris','old'), (' LIMA.','new'), ('PARIS!','old'),
    ('Paris and Lima','neither'), ('Parisian','neither'), ('Limas','neither'), ('','neither'),
    ('Neither city','neither'), ('Not Paris','old'), ('(Lima)','new')])
def test_parser_is_called_unchanged(text,want):
    assert C.classify(text,'Paris','Lima') == want
    original = parse_target_answer({'primary':{'candidates':['Paris','Lima'],'answer':'Paris'}},text)
    assert C.classify(text,'Paris','Lima') == ({'Paris':'old','Lima':'new'}.get(original,'neither'))


def test_orientation_uses_per_item_strings():
    assert C.classify('Paris','Lima','Paris') == 'new'
    assert C.classify('Lima','Lima','Paris') == 'old'


def test_no_new_aliases_or_semantic_negation_rule():
    assert C.classify('City of lights','Paris','Lima') == 'neither'
    assert C.classify('not Lima','Paris','Lima') == 'new'


def test_frozen_pairs_and_e104_strict_tie_rule():
    assert list(map(list,C.PAIR_STRINGS)) == PAIRS['fact_recall']
    assert C.pair_preference_flip([[2,1]],'Paris') is True
    assert C.pair_preference_flip([[2,1]],'Lima') is False
    assert C.pair_preference_flip([[1,2]],'Lima') is True
    assert C.pair_preference_flip([[1,1]],'Lima') is False
    assert C.pair_preference_flip(None,'Lima') is None


def test_text_classifier_and_logits_remain_separate():
    b=dict(id='synthetic',old_value='Paris',new_value='Lima')
    r=dict(id='synthetic',token_ids=[3,4],text='Paris',greedy_max_new_tokens=3,pair_logits=[[0,100]])
    z=C.classify_record(r,b)
    assert z['answer_value']=='old' and z['flipped'] is False
    assert z['pair_preference_flip_descriptive'] is True
    r.update(text='Lima',pair_logits=[[100,0]])
    z=C.classify_record(r,b)
    assert z['answer_value']=='new' and z['flipped'] is True
    assert z['pair_preference_flip_descriptive'] is False


def test_both_is_neither_not_missing():
    z=C.classify_record(dict(id='x',text='Paris Lima',token_ids=[1,2,3],greedy_max_new_tokens=3),
                        dict(id='x',old_value='Paris',new_value='Lima'))
    assert z['answer_value']=='neither' and z['flipped'] is False
    assert z['pair_preference_flip_descriptive'] is None


@pytest.mark.parametrize('patch',[dict(id='wrong'),dict(greedy_max_new_tokens=4),dict(token_ids=[1,2,3,4]),dict(text=None)])
def test_bad_envelopes_refused_not_counted_as_neither(patch):
    r=dict(id='x',text='Paris',token_ids=[1],greedy_max_new_tokens=3)
    r.update(patch)
    with pytest.raises(ValueError):
        C.classify_record(r,dict(id='x',old_value='Paris',new_value='Lima'))


def test_source_mismatch_refused(monkeypatch,tmp_path):
    p=tmp_path/'changed.py';p.write_text('changed')
    monkeypatch.setattr(C.analysis_utils,'__file__',str(p))
    with pytest.raises(ValueError,match='source changed'):
        C.classify('Paris','Paris','Lima')
