import copy
import pytest
from common.stats import wilson
from .analysis import analyze


def grid(n=40,a='X',b='Y'):
    return [{'pair_id':str(i),'blocks':{str(k):{'A':None if a is None else {'values': {'X':['X'],'Y':['Y'],'other':['OTHER'],'none':[]}.get(a,[a])},'B':None if b is None else {'values': {'X':['X'],'Y':['Y'],'other':['OTHER'],'none':[]}.get(b,[b])}} for k in (44,52,60)}} for i in range(n)]


def test_tracking_exact_wilson():
    r=analyze(grid())['blocks']['60'];assert r['tracking']['k']==40 and r['prior']['k']==0
    assert r['tracking']['Wilson95']==list(wilson(40,40)[1:]);assert r['tracking_reading'] is True

@pytest.mark.parametrize('value',['X','Y'])
def test_prior(value):
    r=analyze(grid(a=value,b=value))['blocks']['60'];assert r['prior']['estimate']==1 and r['tracking']['estimate']==0


def test_reverse_not_tracking_or_prior():
    r=analyze(grid(a='Y',b='X'))['blocks']['44'];assert r['tracking']['k']==r['prior']['k']==0

@pytest.mark.parametrize('value',['other','none'])
def test_observed_non_xy_excluded(value):
    r=analyze(grid(a=value,b='Y'))['blocks']['60'];assert r['eligible_pairs']==0
    assert r['tracking']['estimate'] is None and r['xy_coverage']['estimate']==.5 and r['coverage']['missing_n']==0
    assert r['categories'][value]['k']==40
    assert r['coverage']['estimate']==(1 if value=='other' else .5)


def test_missing_not_none():
    r=analyze(grid(a=None))['blocks']['60'];assert r['coverage']['missing_n']==40 and r['unknown_pairs']==40
    assert r['categories']['none']['k']==0 and r['both_value_pair_coverage']['n']==0


def test_no_cross_block_filter():
    g=grid();g[0]['blocks']['44']['A']=None;r=analyze(g)
    assert r['blocks']['44']['eligible_pairs']==39 and r['blocks']['60']['eligible_pairs']==40


def test_mixed_denominator():
    g=grid();g[:10]=grid(10,a='X',b='X')
    g[10]['blocks']['60']['A']={'values':['OTHER']}
    r=analyze(g)['blocks']['60'];assert r['tracking']['n']==39 and r['tracking']['k']==29 and r['prior']['k']==10

@pytest.mark.parametrize('n',[0,39,85])
def test_screen_only_and_excess_rejected(n):
    with pytest.raises(ValueError):analyze(grid(n))


def test_duplicate_pair_rejected():
    g=grid();g[1]['pair_id']=g[0]['pair_id']
    with pytest.raises(ValueError):analyze(g)


def test_bad_code_rejected():
    with pytest.raises(ValueError):analyze(grid(a='BOTH'))


def test_wrong_policy_rejected():
    with pytest.raises(ValueError):analyze(grid(),'identified_other')


def test_full_84_and_ceiling():
    r=analyze(grid(84));assert r['blocks']['52']['coverage']['planned_n']==168 and r['ceiling']['construction_only']

from .run import verify_selection

def screen():
    return [dict(pair_id=str(i),generation_index=i,greedy_max_new_tokens=32,answer_A='x' if i<84 else '',answer_B='y') for i in range(600)]

def selected():return [dict(pair_id=str(i),X='x',Y='y') for i in range(84)]

def test_exact_screen_selection():verify_selection(screen(),selected())

@pytest.mark.parametrize('drift',['order','label','cap','missing','selection'])
def test_screen_drift(drift):
    s,p=screen(),selected()
    if drift=='order':s[0]['generation_index']=1
    if drift=='label':p[0]['X']='z'
    if drift=='cap':s[0]['greedy_max_new_tokens']=3
    if drift=='missing':s.pop()
    if drift=='selection':p.reverse()
    with pytest.raises(ValueError):verify_selection(s,p)


def test_first300_exact_parent():
    verify_selection(screen()[:300],selected(),[str(i) for i in range(600)])

@pytest.mark.parametrize('drift',['later_half','parent_duplicate','parent_short','screen_short','screen_full'])
def test_first300_rejects_scope_drift(drift):
    s=screen()[:300];parent=[str(i) for i in range(600)]
    if drift=='later_half':s=[dict(x,pair_id=str(i+300)) for i,x in enumerate(s)]
    if drift=='parent_duplicate':parent[-1]=parent[0]
    if drift=='parent_short':parent.pop()
    if drift=='screen_short':s.pop()
    if drift=='screen_full':s=screen()
    with pytest.raises(ValueError):verify_selection(s,selected(),parent)

def test_first300_requires_explicit_scope():
    with pytest.raises(ValueError):verify_selection(screen()[:300],selected())

@pytest.mark.parametrize('values',[['X','Y'],['X','OTHER'],['Y','OTHER'],['X','Y','OTHER']])
@pytest.mark.parametrize('partner',[None,[],['OTHER'],['X'],['Y'],['Y','OTHER']])
def test_multiple_primary_and_sensitivity(values,partner):
    g=grid()
    g[0]['blocks']['60']={'A':{'values':values},'B':None if partner is None else {'values':partner}}
    r=analyze(g)['blocks']['60']
    assert r['eligible_pairs']==39 and r['tracking']['k']==39
    assert r['tracking']['estimate']==1 and r['prior']['k']==0
    assert r['multiple_pairs']==1 and r['multiple_readouts']==1+int(partner==['Y','OTHER'])
    assert r['sensitivity']['tracking']['n']==40 and r['sensitivity']['tracking']['k']==39
    assert r['sensitivity']['prior']['n']==40 and r['sensitivity']['prior']['k']==0
    assert r['sensitivity']['tracking']['Wilson95']==list(wilson(39,40)[1:])
    assert r['coverage']['k']==79+int(bool(partner))
    assert r['sensitivity']['used_for_verdict'] is False
    assert analyze(g)['blocks']['44']['eligible_pairs']==40


def test_sensitivity_does_not_change_primary_verdict():
    g=grid()
    for row in g[:20]:row['blocks']['60']['A']={'values':['X','Y']}
    r=analyze(g)['blocks']['60']
    assert r['tracking_reading'] is True
    assert r['sensitivity']['tracking']['estimate']==.5
    assert r['categories']['multiple']['k']==20


def test_all_multiple_no_primary_denominator():
    g=grid()
    for row in g:row['blocks']['60']['A']={'values':['X','OTHER']}
    r=analyze(g)['blocks']['60']
    assert r['tracking']['estimate'] is None and r['prior']['estimate'] is None
    assert r['sensitivity']['tracking']['estimate']==0 and r['coverage']['estimate']==1
