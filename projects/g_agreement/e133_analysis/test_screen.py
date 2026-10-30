from copy import deepcopy
import pytest
from . import screen as s


def raw(text,id=None):return dict(id=id,text=text,token_ids=[1,2],greedy_max_new_tokens=32)


def candidates(n=90,one=45):
    ps=[];answers={}
    for i in range(n+one):
        members=[dict(member=j,item_id=f'{i}:{j}',current=name,previous='Dana')for j,name in enumerate(['Erin','Carl'])]
        ps.append(dict(pair_id=str(i),generation_index=i,kind='multi_hop'if i<n else'one_hop',members=members))
        for m in members:answers[m['item_id']]=raw(m['current'],m['item_id'])
    return ps,answers


def test_unchanged_matcher_32token_no_alias_or_punctuation_repair():
    cs=['Erin','Carl','Dana']
    assert s.classify(raw('\n<think>\nErin'),cs)=='Erin'
    assert s.classify(raw('Erin and Dana'),cs)is None
    assert s.classify(raw('Dana'),cs)=='Dana'
    assert s.classify(raw('neither'),cs)is None and s.classify(None,cs)is None
    for record in [dict(raw('Erin'),greedy_max_new_tokens=3),dict(raw('Erin'),token_ids=[1]*33)]:
        with pytest.raises(ValueError):s.classify(record,cs)


def test_first_correct_pairs_and_both_members_frozen_order():
    pairs,answers=candidates();answers['0:1']=raw('Dana','0:1');before=deepcopy(answers)
    r=s.select(list(reversed(pairs)),answers)
    assert r['selected']['multi_hop']==[str(i)for i in range(1,85)]
    assert r['selected']['one_hop']==[str(i)for i in range(90,132)]
    assert r['qualifying_counts']==dict(multi_hop=89,one_hop=45)and answers==before
    assert r['informative']


def test_missing_fewer_qualifying_never_refilled_from_reader():
    pairs,answers=candidates(49,10);answers.pop('0:0')
    r=s.select(pairs,answers);assert len(r['selected']['multi_hop'])==48 and not r['informative']
    assert len(r['selected']['one_hop'])==10


def test_duplicate_identity_and_invalid_previous_failclosed():
    pairs,answers=candidates(2,1);pairs[1]['generation_index']=0
    with pytest.raises(ValueError):s.select(pairs,answers)
    pairs,answers=candidates(2,1);pairs[0]['members'][0]['previous']='Erin'
    with pytest.raises(ValueError):s.select(pairs,answers)


def test_qa2_separate_first42_and_qa3_ineligible_without_answer_rewrite():
    ps,answers=candidates(50,45)
    for j,p in enumerate(ps[50:]):p.update(kind='babi_qa2',task='qa2',source_split='test',source_episode_id='episode:'+str(j//2))
    ps.append(dict(pair_id='QA3-ineligible',generation_index=1000,kind='babi_qa3',members=[]))
    r=s.select(ps,answers)
    assert len(r['selected']['multi_hop'])==50 and len(r['selected']['babi_qa2'])==42
    assert r['screening'][-1]['ineligible_reason'].startswith('QA3')


def test_screen_record_identity_never_joined_by_position():
    ps,answers=candidates(2,1);answers['0:0']['id']='wrong-source-item'
    with pytest.raises(ValueError,match='screening answer IDs'):s.select(ps,answers)
