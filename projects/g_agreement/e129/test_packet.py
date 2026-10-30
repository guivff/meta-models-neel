import copy
import pytest
from .build import compose,facts_from_source,ISO_CATALOG
from .selection import select_on_unprefixed


class Words:
    def __init__(self):self.vocab={}
    def encode(self,text,**kwargs):
        return [self.vocab.setdefault(word,len(self.vocab))for word in text.split()]


def facts():
    return [dict(iso=f'X{i}',entity=f'Country{i}',value=f'City{i}',relation='capital')for i in range(100)]


def test_seeded_complete_pool_donors_and_prefix_lengths_no_selection():
    source=facts();before=copy.deepcopy(source)
    xs,labels=compose(source,Words());again=compose(source,Words())
    assert (xs,labels)==again and source==before and len(xs)==300 and len(labels)==100
    by={x['id']:x for x in xs}
    for x in labels:
        assert x['old_value']!=x['new_value'] and x['iso']!=x['donor_iso']
        assert x['entity']not in (x['neutral_entity'],x['donor_entity'])
        assert x['neutral_entity']!=x['donor_entity']
        a,b,z=[by[x['condition_ids'][c]]for c in ('context_update','neutral_prefix','none')]
        assert len(a['ids'])==len(b['ids'])
        assert a['ids'][-len(z['ids']):]==z['ids']==b['ids'][-len(z['ids']):]
        assert all(y['candidate_ids']==[] for y in (a,b,z))


def test_only_unprefixed_true_answers_first84_no_other_measure():
    _,labels=compose(facts(),Words())
    raw=[dict(id=x['condition_ids']['none'],text=x['old_value'],token_ids=[1],greedy_max_new_tokens=3,pair_logits=[[0,999]])for x in labels]
    r=select_on_unprefixed(labels,raw)
    assert r['selected_n']==84 and r['selected_base_ids']==[x['base_id']for x in labels[:84]]
    raw[0]['text']=labels[0]['new_value']
    r=select_on_unprefixed(labels,raw)
    assert r['selected_base_ids']==[x['base_id']for x in labels[1:85]]
    assert r['counts']==dict(old=99,new=1,neither=0,missing=0)


def test_prefix_answers_are_rejected_and_missing_not_imputed():
    _,labels=compose(facts(),Words());x=labels[0]
    with pytest.raises(ValueError):select_on_unprefixed(labels,[dict(id=x['condition_ids']['context_update'])])
    r=select_on_unprefixed(labels,[])
    assert r['selected_n']==0 and r['counts']['missing']==100 and r['counts']['old']==0


def test_duplicate_and_bad_generation_envelopes_refused():
    _,labels=compose(facts(),Words());x=labels[0]
    r=dict(id=x['condition_ids']['none'],text=x['old_value'],token_ids=[1],greedy_max_new_tokens=3)
    with pytest.raises(ValueError):select_on_unprefixed(labels,[r,r])
    r['token_ids']=[1,2,3,4]
    with pytest.raises(ValueError):select_on_unprefixed(labels,[r])


def test_no_silent_missing_country_or_original_FR_PE():
    assert 'FR'not in ISO_CATALOG and 'PE'not in ISO_CATALOG
    with pytest.raises(ValueError):facts_from_source('AD\tAND\t020\tAN\tAndorra\tAndorra la Vella')
