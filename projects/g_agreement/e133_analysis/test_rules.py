from copy import deepcopy
import pytest
from . import rules as r


def state(which):return {k:int(k==which)for k in ['current','previous','other','none','dual_current_previous']}


def pairs(n=50,one=2):
    result=[]
    for i in range(n+one):
        kind='multi_hop'if i<n else'one_hop';members=[]
        for j in (0,1):
            own=-1 if j==0 else 1;other=-own
            patches={b:{p:own+(.1 if p!='read_token'or b==44 else .6)*(other-own)for p in r.PATCHES}for b in (r.BLOCKS if kind=='multi_hop'else(44,52))}
            members.append(dict(member=j,own_logodds=own,patches=patches,readouts={44:state('previous'if i<30 else'current'if i<40 else'none'),52:state('current'),60:state('current')}))
        result.append(dict(pair_id=str(i),generation_index=i,kind=kind,members=members))
    return result


def test_rnl1_both_controls_allfive_and_onehop_descriptive():
    xs=pairs();before=deepcopy(xs);out,private=r.analyze(xs,draws=40)
    assert out['R_NL1']=='MET'and out['falsifier']=='NOT MET'and out['informative']
    assert out['groups']['multi_hop']['reader_rates']['44']['previous']['estimate']==.6
    assert set(out['groups']['one_hop']['patches'])=={44,52}and xs==before
    assert private and out['bootstrap']['unit'].startswith('matched source pair')
    for x in xs[:50]:
        for m in x['members']:m['patches'][60]['earlier_token']=m['own_logodds']+.2*(-2*m['own_logodds'])
    assert r.analyze(xs,draws=20)[0]['R_NL1']=='NOT MET'


def test_falsifier_either_reader_or_early_patch_no_added_controlgate():
    xs=pairs()
    for x in xs[:50]:
        for m in x['members']:m['readouts'][44]=state('current')
    assert r.analyze(xs,draws=20)[0]['falsifier']=='MET'
    xs=pairs()
    for x in xs[:50]:
        for m in x['members']:
            m['patches'][44]['read_token']=0
            m['patches'][60]['random_norm_matched']=-m['own_logodds']
    assert r.analyze(xs,draws=20)[0]['falsifier']=='MET'


def test_gate_and_missing_judgments_and_zero_denominator_not_zero():
    assert r.analyze(pairs(49),draws=10)[0]['R_NL1']=='DESCRIPTIVE ONLY'
    xs=pairs();xs[0]['members'][0]['readouts'][44]=None
    out,_=r.analyze(xs,draws=20)
    assert out['groups']['multi_hop']['reader_rates']['44']['previous']['missing_n']==1
    assert out['groups']['multi_hop']['reader_rates']['44']['previous']['planned_n']==100
    xs=pairs();xs[0]['members'][0]['own_logodds']=1
    out,_=r.analyze(xs,draws=20);assert out['R_NL1']=='NOT EVALUABLE'
    assert out['groups']['multi_hop']['patches'][44]['read_token']['estimate']is None
    assert r.ratio(1,1,2)is None and r.ratio(-2,2,0)==.5


def test_pair_bootstrap_does_not_resample_members_independently():
    x=r.paired_median([[0,1],[2,3]],draws=100)
    assert x['estimate']==1.5 and x['CI95']==[.5,2.5]
    assert r.paired_median([[None,1],[2,3]],draws=10)['estimate']is None


def test_original_e104_evidence_exclusive_dual_and_missing():
    value_map={'A':'Erin','B':'Dana','C':'Carl'}
    def code(vals,cat='states_value',evidence='Erin Dana'):return dict(category=cat,values=vals,evidence=evidence)
    text='Erin Dana Carl'
    z=r.readout(code(['A','B']),text,value_map,'Erin','Dana')
    assert z['current']==z['previous']==0 and z['dual_current_previous']==z['other']==1
    assert r.readout(code(['B']),text,value_map,'Erin','Dana')['previous']==1
    assert r.readout(code(['C']),text,value_map,'Erin','Dana')['other']==1
    assert r.readout(code([],cat='silent',evidence=''),'',value_map,'Erin','Dana')['none']==1
    assert r.readout(None,text,value_map,'Erin','Dana')is None
    assert r.readout(code([],cat='UNPARSEABLE',evidence=''),text,value_map,'Erin','Dana')is None
    with pytest.raises(ValueError):r.readout(code(['A'],evidence='absent'),text,value_map,'Erin','Dana')


def test_registered_threshold_boundaries_and_strict_lower_bound():
    stat=lambda p,lo:dict(estimate=p,Wilson95=[lo,1])
    reads={'44':{'previous':stat(.30,.20001),'current':stat(.40,.3)},'60':{'current':stat(.70,.6)}}
    patches={b:{c:dict(estimate=.15,CI95=[.01,.2])for c in r.PATCHES}for b in r.BLOCKS}
    patches[52]['read_token']=dict(estimate=.50,CI95=[.25001,.7])
    assert r.classify(reads,patches,True)['R_NL1']=='MET'
    reads['44']['previous']['Wilson95'][0]=.20
    assert r.classify(reads,patches,True)['R_NL1']=='NOT MET'
    reads['44']['previous']['Wilson95'][0]=.20001
    patches[52]['read_token']['CI95'][0]=.25
    assert r.classify(reads,patches,True)['R_NL1']=='NOT MET'


def test_qa2_descriptive_never_pooled_into_rnl1():
    xs=pairs(53,0)
    for x in xs[50:]:
        x['kind']='babi_qa2';x['source_episode_id']='episode:'+str(int(x['pair_id'])//2)
        for m in x['members']:m['readouts'][44]=state('current')
    result,_=r.analyze(xs,draws=20)
    assert result['R_NL1']=='MET'and result['groups']['multi_hop']['n_pairs']==50
    assert result['groups']['babi_qa2']['n_pairs']==3 and result['groups']['babi_qa2']['descriptive']
    assert result['groups']['babi_qa2']['threshold_pattern_descriptive']['falsifier']=='MET'


def test_qa2_bootstrap_preserves_whole_episode_not_independent_pairs():
    x=r.episode_median([[0,0],[0,0],[10,10],[10,10]],['A','A','B','B'],draws=100)
    assert x['estimate']==5 and x['CI95']==[0,10]and x['n_episodes']==2
    assert x['bootstrap_unit'].startswith('source episode')
    assert r.episode_median([[.5,.5]],['only'],draws=10)['CI95']is None
    assert r.episode_median([[None,.5],[.5,.5]],['A','B'],draws=10)['estimate']is None


def test_qa2_reader_ci_matches_rq_whole_episode_prototype():
    import numpy as np
    values=[0,0,0,0,1,1];episodes=['A']*4+['B']*2
    got=r.episode_rate(values,episodes)
    rng=np.random.default_rng(20261027)
    arrays=[[0,0,0,0],[1,1]]
    stats=[np.mean([v for k in draw for v in arrays[k]])for draw in rng.integers(0,2,(2000,2))]
    assert got['estimate']==1/3 and got['CI95']==np.quantile(stats,[.025,.975]).tolist()==[0.,1.]
    assert got['n_episodes']==2 and got['defined_draws']==2000 and got['undefined_draws']==0
    assert got['planned_n']==6 and got['n']==6 and got['k']==2 and 'Wilson95'not in got


def test_qa2_reader_missing_denominator_undefined_draws_no_zero_imputation():
    got=r.episode_rate([None,None,1,1],['A','A','B','B'])
    assert got['estimate']==1 and got['n']==2 and got['missing_n']==2 and got['planned_n']==4
    assert 0<got['undefined_draws']<2000 and got['defined_draws']+got['undefined_draws']==2000
    assert got['CI95']is None
    for values,episodes in [([],[]),([None,None],['A','A'])]:
        z=r.episode_rate(values,episodes)
        assert z['estimate']is None and z['CI95']is None and z['defined_draws']==0
    with pytest.raises(ValueError):r.episode_rate([1],[None])


def test_qa2_reader_change_leaves_synthetic_analysis_byte_equivalent():
    xs=pairs(50,2);baseline=r.analyze(xs,draws=100)[0]
    qa=deepcopy(xs[:4])
    for i,x in enumerate(qa):
        x.update(pair_id='qa:'+str(i),kind='babi_qa2',source_episode_id='A'if i<2 else'B')
        for m in x['members']:m['readouts'][44]=state('current'if i<2 else'previous')
    combined=r.analyze(xs+qa,draws=100)[0]
    for key in ['multi_hop','one_hop']:assert combined['groups'][key]==baseline['groups'][key]
    for key in ['R_NL1','falsifier','informative']:assert combined[key]==baseline[key]
    for layer in r.READS:
        for stat in combined['groups']['babi_qa2']['reader_rates'][str(layer)].values():
            assert 'CI95'in stat and 'Wilson95'not in stat and stat['n_episodes']==2
    assert combined['groups']['babi_qa2']['reader_rates']['44']['current']['CI95']==[0.,1.]
