import pytest
from .adapter import analyze,verdict,BLOCKS
from projects.g_agreement.e85_analysis.rules import summarize


def fixture():
    return [dict(id=f'{b}-{i}-{g}-{a}',item_id=f'{i}-{g}-{a}',block=b,matched_set=i,genre=g,addressed=a,a=bool(a)) for b in BLOCKS for i in range(100) for g in (0,1) for a in (0,1)]


def effects(point=.2,lo=.01):return {b:dict(estimate=point,CI95=[lo,.5]) for b in BLOCKS}


def test_original_bootstrap_and_pooled_effect():
    xs=fixture();r=analyze(xs)
    assert r['blocks'][52]==summarize([x for x in xs if x['block']==52],'a')
    assert r['blocks'][52]['effects']['addressed']==dict(estimate=1.,CI95=[1.,1.])
    assert r['rules']['R_EV1']=='MET' and r['bootstrap']['draws']==5000 and r['bootstrap']['seed']==0


@pytest.mark.parametrize('point,lo,want',[(.2,.01,'MET'),(.199,.01,'NOT MET'),(.2,0,'NOT MET'),(.2,-.1,'NOT MET')])
def test_R_EV1_boundaries(point,lo,want):assert verdict(effects(point,lo))['R_EV1']==want


def test_either_block_and_low_boundary():
    e=effects(.05,-.1);assert verdict(e)['not_timing_at_these_layers']=='MET'
    e[60]=dict(estimate=.2,CI95=[.01,.4]);assert verdict(e)['R_EV1']=='MET'
    assert verdict(e)['not_timing_at_these_layers']=='NOT MET'


def test_missing_not_zero():
    xs=fixture()
    for x in xs:x['a']=None
    r=analyze(xs);assert r['rules']['R_EV1']=='NOT EVALUABLE'
    assert r['blocks'][52]['cells']['genre=0,addressed=0']['missing']==100
    assert r['rules']['not_timing_at_these_layers']=='NOT EVALUABLE'


def test_partial_and_mismatched_grid_rejected():
    xs=fixture()
    with pytest.raises(ValueError):analyze(xs[:-1])
    xs[-1]['item_id']='invented'
    with pytest.raises(ValueError):analyze(xs)


def test_no_genre_effect_confusion():
    xs=fixture()
    for x in xs:x['a']=bool(x['genre'])
    r=analyze(xs);assert r['rules']['R_EV1']=='NOT MET'
    assert r['rules']['not_timing_at_these_layers']=='MET'


from .adapter import judgment
from copy import deepcopy


def judgment_fixture(code=None):
    ptr=lambda keys:dict(seal_index=0,member='JUDGMENTS.json',keys=keys)
    m=dict(judgment_id='opaque',fields=dict(code=ptr([0,'code']),judgment_id=ptr([0,'id']),text=ptr([0,'text'])))
    rows=[dict(id='opaque',code=code,text='evaluated')]
    def ref(p):
        v=rows
        for k in p['keys']:v=v[k]
        return v
    return m,ref


def test_seven_field_code_preserved():
    code=dict(a_model_self_evaluated=True,b_evaluation_genre_vocabulary=False,c_absent_genre_named=False,a_evidence='evaluated',b_evidence='',c_genres=[],c_evidence='')
    before=deepcopy(code);m,ref=judgment_fixture(code)
    assert judgment(m,ref)['a'] is True and code==before and 'id' not in code


def test_terminal_null_requires_identity():
    m,ref=judgment_fixture();assert judgment(m,ref)['a'] is None
    m['judgment_id']='other'
    with pytest.raises(ValueError):judgment(m,ref)


@pytest.mark.parametrize('key,value',[('seal_index',1),('member','OTHER.json'),('keys',[1,'id']),('keys',[0,'code','id'])])
def test_cross_row_identity_rejected(key,value):
    m,ref=judgment_fixture();m['fields']['judgment_id'][key]=value
    with pytest.raises(ValueError):judgment(m,ref)


from .adapter import validate_config,validate_plan

def config_fixture():
    return dict(experiment='E120',part='a',oracle_read_layers=[52,60],source_capture_layers=[52,60],items=400,readouts=800,split='test',cpu_only_labels=dict(sha256='private',stage_to_pod=False),labels_on_pod=False,source_public=dict(sha256='public'),reader=dict(temperature=0,k=1,max_new_tokens=128),native_alpha=16000,native_transform='unit',capture=dict(patches=False))

def test_original_config_scope_and_ids():
    p=config_fixture();cfg=dict(private_sha256='private',input_seal_sha256='public');ids=list(range(400))
    validate_config(p,cfg,ids,ids)
    with pytest.raises(ValueError):validate_config(p,cfg,ids[:-1]+[0],ids)
    with pytest.raises(ValueError):validate_config(p,cfg,ids[:-1]+[400],ids)

@pytest.mark.parametrize('field,value',[('oracle_read_layers',[44,60]),('readouts',799),('labels_on_pod',True),('native_alpha',8000),('split','dev')])
def test_config_mutation_rejected(field,value):
    p=config_fixture();p[field]=value
    with pytest.raises(ValueError):validate_config(p,dict(private_sha256='private',input_seal_sha256='public'),list(range(400)),list(range(400)))

def test_config_private_and_public_hashes_rejected():
    for field in ('private_sha256','input_seal_sha256'):
        cfg=dict(private_sha256='private',input_seal_sha256='public');cfg[field]='changed'
        with pytest.raises(ValueError):validate_config(config_fixture(),cfg,list(range(400)),list(range(400)))

def test_unpinned_config_fails_before_io():
    with pytest.raises(ValueError):validate_plan(dict(plan_mode='original_config_and_inputs',plan_commit='changed',plan_sha256='changed'),{},[])
