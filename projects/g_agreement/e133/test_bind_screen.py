import copy
from projects.g_agreement.e133.bind_screen import adapt
from projects.g_agreement.e133.test_public import Tok

def test_recipient_tokens_ascending_identical_bothmembers_truth_cpu_only():
    public=[dict(id='a',prompt='read by'),dict(id='b',prompt='read by')]
    pairs=[dict(pair_id='p',family='multi_hop',recipients=['Bob','Alice'],previous_holder='Dana',members=[dict(id='a',member=0,current_holder='Bob',previous_holder='Dana'),dict(id='b',member=1,current_holder='Alice',previous_holder='Dana')])]
    before=copy.deepcopy((public,pairs));xs,cpu=adapt(public,pairs,Tok(),'synthetic')
    assert (public,pairs)==before and xs[0]['candidate_ids']==xs[1]['candidate_ids']==[[[100],[101]]]
    assert cpu[0]['current_recipient_index']==0 and cpu[1]['current_recipient_index']==1
    assert all(set(x)=={'id','pair_id','family','member','ids','read_index','candidate_ids'}for x in xs)
    assert all('Dana'not in str(x)and 'previous'not in x and 'current'not in x for x in xs)


def test_babi_same_structure_no_previous_token_staged():
    pub=[dict(id='a',prompt='Answer:'),dict(id='b',prompt='Answer:')]
    pairs=[dict(pair_id='p',member_ids=['a','b'],original_current='office',twin_current='garden',previous='bedroom')]
    xs,c=adapt(pub,pairs,Tok(),'babi');assert {x['family']for x in xs}=={'babi'}
    a,b=xs[0]['candidate_ids'][0];assert a[0]<b[0]and xs[0]['candidate_ids']==xs[1]['candidate_ids']
    assert c[0]['previous']=='bedroom'
