import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('r5_e140',Path(__file__).with_name('reproduce_e140.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from projects.g_agreement.e140_analysis.analysis import analyze
from projects.g_agreement.e140_analysis.test_analysis import grid, screen, selected
from reproduce_e118b import compare

@pytest.mark.parametrize('a,b',[('X','Y'),('X','X'),('Y','Y'),('Y','X'),('other','other'),('none','Y'),(None,'Y')])
def test_independent_all_fields(a,b):
    rows=grid(a=a,b=b)
    compare(m.reproduce(rows),analyze(rows))

def test_mixed_no_cross_block_filter_or_other_credit():
    rows=grid(84)
    for i,row in enumerate(rows):
        for block in ('44','52','60'):
            if i%7==0:row['blocks'][block]['A']=None
            elif i%7==1:row['blocks'][block]['A']={'values':['OTHER']}
            elif i%7==2:row['blocks'][block]['B']={'values':['X']}
            elif i%7==3:row['blocks'][block]['A']={'values':['Y']};row['blocks'][block]['B']={'values':['X']}
    rows[6]['blocks']['44']['A']=None
    out=m.reproduce(rows);compare(out,analyze(rows))
    assert out['blocks']['44']['eligible_pairs']!=out['blocks']['60']['eligible_pairs']
    assert out['blocks']['60']['coverage']['n']<168

def test_literal_selection():
    m.selected_pairs(screen(),selected())
    wrong=selected();wrong[0]['X']='changed'
    with pytest.raises(ValueError):m.selected_pairs(screen(),wrong)
    wrong=screen();wrong[0]['generation_index']=1
    with pytest.raises(ValueError):m.selected_pairs(wrong,selected())

@pytest.mark.parametrize('n',[0,39,85])
def test_no_analysis_for_wrong_size(n):
    with pytest.raises(ValueError):m.reproduce(grid(n))


def test_authorized_first300_scope_preserves_selection():
    from projects.g_agreement.e140_analysis.test_analysis import screen, selected
    from projects.g_agreement.e140_analysis.run import verify_selection
    parent = [str(i) for i in range(600)]
    m.selected_pairs(screen()[:300], selected(), parent)
    verify_selection(screen()[:300], selected(), parent)
    for rows,ids in [(screen()[300:],parent), (screen()[:299],parent),
                     (screen(),parent), (screen()[:300],parent[:-1]),
                     (screen()[:300],parent[:-1]+[parent[0]])]:
        with pytest.raises(ValueError):m.selected_pairs(rows,selected(),ids)
    with pytest.raises(ValueError):m.selected_pairs(screen()[:300],selected())


def test_native_index_transport_literal_no_rewrite():
    import copy
    from projects.g_agreement.e140_analysis.test_native_index import fixture
    p,i,n,x=fixture();before=copy.deepcopy(n)
    m.validate_native_index(p,i,n,44,lambda _:x)
    assert n==before and 'id' not in n
    m.validate_native_index({},dict(native_id='old'),dict(id='old'),44,lambda _:None)
    for target,key,value in [('x','id','wrong'),('x','block',52),('x','kind','capture'),('x','record',True),
                             ('x','record',-1),('x','member','other.json'),('n','id','wrong'),
                             ('np','seal_index',1),('np','keys',[1]),('ip','member','main/OTHER.json')]:
        p,i,n,x=fixture();{'x':x,'n':n,'np':p['native'],'ip':p['native_index']}[target][key]=value
        with pytest.raises(ValueError):m.validate_native_index(p,i,n,44,lambda _:x)


@pytest.mark.parametrize('values',[['X','Y'],['X','OTHER'],['Y','OTHER'],['X','Y','OTHER']])
@pytest.mark.parametrize('partner',[None,[],['OTHER'],['X'],['Y'],['Y','OTHER']])
def test_independent_multiple_primary_and_every_pair_sensitivity(values,partner):
    rows=grid()
    rows[0]['blocks']['60']={'A':{'values':values},'B':None if partner is None else {'values':partner}}
    actual=m.reproduce(rows);compare(actual,analyze(rows))
    r=actual['blocks']['60']
    assert r['eligible_pairs']==39 and r['tracking']['k']==39
    assert r['sensitivity']['eligible_pairs']==40 and r['sensitivity']['tracking']['k']==39
    assert r['sensitivity']['used_for_verdict'] is False
    assert r['multiple_pairs']==1


def test_multiple_cannot_change_primary_reading():
    rows=grid()
    for r in rows[:20]:r['blocks']['60']['A']={'values':['X','Y']}
    a=m.reproduce(rows);compare(a,analyze(rows))
    assert a['blocks']['60']['tracking_reading'] is True
    assert a['blocks']['60']['sensitivity']['tracking']['estimate']==.5


def test_original_producer_record_lossless_validation():
    import copy,itertools
    for size in (1,2,3):
        for values in itertools.combinations(('X','Y','OTHER'),size):
            j=dict(id='j',status='KEPT',code=dict(id='j',category='states_value',values=list(values),evidence='sample'))
            before=copy.deepcopy(j);assert m.original_record(j,'sample')==j['code']and j==before
    assert m.original_record(dict(id='j',status='UNPARSEABLE',code=None),'')is None
    j=dict(id='j',status='KEPT',code=dict(id='j',category='states_value',values=['X'],evidence='sample'))
    for field,value in [('id','wrong'),('values',['X','X']),('values','X'),('evidence','absent'),('category','silent')]:
        x=copy.deepcopy(j);x['code'][field]=value
        with pytest.raises(ValueError):m.original_record(x,'sample')
