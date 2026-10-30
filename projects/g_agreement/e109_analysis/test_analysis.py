import copy
import numpy as np
import pytest
from . import analysis as a
from . import adapter as d

def fixture():
    data={}
    for row in a.ROWS:
        labels=np.array([0,1]*42);x=(labels*2-1)[:,None].astype(float)
        ids=[f't{i}' for i in range(84)];cohort=ids[:84 if row=='fact_recall' else 50]
        layers={}
        for l in a.LAYERS:
            z=dict(dev_unhooked=x,test=dict(unhooked=x,steered=-x,random=x))
            if l in a.READS:z['oracle']=dict(steered=[1]*84,random=[0]*84)
            layers[l]=z
        data[row]=dict(dev_ids=[f'd{i}' for i in range(84)],dev_labels=labels.tolist(),test_ids=ids,targets=(1-labels).tolist(),cohort=cohort,layers=layers)
    return data

def test_full_fit_cohort_wilson_and_old_vs_new44():
    out=a.analyze(fixture(),dict(fact_recall=.18,language_plan=.14))
    assert out['rules']['R-AR1']['status']=='MET'
    assert out['rules']['R-AR2']['status']=='MET'
    assert out['rules']['falsifier']['status']=='MET'
    assert out['rows']['language_plan'][44]['probe']['steered']['n']==50
    assert out['rows']['fact_recall'][44]['probe']['steered']['CI95'][0]<1
    assert out['rows']['fact_recall'][44]['oracle']['difference']['CI95']==[1,1]

def test_dev_fit_unchanged_by_hooked_test():
    z=fixture()['fact_recall'];m=a.fit(z['layers'][44]['dev_unhooked'],z['dev_labels']);w=m.coef_.copy()
    m.predict(np.ones((84,1))*999);assert np.array_equal(w,m.coef_)
    with pytest.raises(ValueError):a.fit(np.ones((83,1)),[0,1]*41+[0])

def test_scope_missing_and_identity():
    data=fixture();data['language_plan']['cohort']=data['language_plan']['test_ids']
    with pytest.raises(ValueError):a.analyze(data,dict.fromkeys(a.ROWS,.1))
    data=fixture();data['fact_recall']['dev_ids'][0]='t0'
    with pytest.raises(ValueError):a.analyze(data,dict.fromkeys(a.ROWS,.1))
    data=fixture();data['fact_recall']['layers'][48]['oracle']={}
    with pytest.raises(ValueError):a.analyze(data,dict.fromkeys(a.ROWS,.1))

def test_rules_boundary_and_layer_match():
    p={r:{l:.7 for l in a.LAYERS} for r in a.ROWS};s={r:{l:dict(estimate=.3,CI95=[.01,.5]) for l in a.READS} for r in a.ROWS}
    assert a.classify_rules(p,s,dict.fromkeys(a.ROWS,.3))['R-AR2']['status']=='NOT MET'
    for r in a.ROWS:
        s[r][52]['CI95'][0]=0;s[r][60]['estimate']=.29
    assert a.classify_rules(p,s,dict.fromkeys(a.ROWS,.1))['R-AR1']['status']=='NOT MET'
    for r in a.ROWS:
        p[r]={l:.49 for l in a.LAYERS}
    assert a.classify_rules(p,s,dict.fromkeys(a.ROWS,.1))['R-AR3']['status']=='MET'
    for r in a.ROWS:p[r][48]=.5
    assert a.classify_rules(p,s,dict.fromkeys(a.ROWS,.1))['R-AR3']['status']=='NOT MET'

def test_missing_is_unknown_not_silent():
    data=fixture()
    for row in a.ROWS:
        for l in a.READS:data[row]['layers'][l]['oracle']['steered']=[None]*84
    out=a.analyze(data,dict.fromkeys(a.ROWS,.1))
    assert out['rules']['falsifier']['status']=='NOT EVALUABLE'
    assert out['rows']['language_plan'][44]['oracle']['missing']['steered']==50

def test_seal_tamper_and_once(tmp_path):
    d.core.write(tmp_path/'raw.json',dict(x=1));d.core.seal(tmp_path,'SEAL.json');h=d.core.sha(tmp_path/'SEAL.json')
    d.core.write(tmp_path/'raw.json',dict(x=2))
    with pytest.raises(ValueError):d.core.verify(tmp_path/'SEAL.json',h)
    s=dict(analysis=str(tmp_path/'out'),guard=str(tmp_path/'guard'),output_sha256='synthetic');d.core.claim(s,'synthetic')
    with pytest.raises((ValueError,FileExistsError)):d.core.claim(s,'synthetic')


def test_redaction_companion_preserves_primary_and_grid():
    from .sensitivity import sensitivity
    data=fixture();old=dict.fromkeys(a.ROWS,.1);primary=a.analyze(data,old);before=copy.deepcopy(primary)
    report=sensitivity(data,primary,old,[dict(row='fact_recall',layer=44,condition='steered',item_id='t0')])
    assert primary==before and data['fact_recall']['layers'][44]['oracle']['steered'][0]==1
    assert report['affected_readouts']==report['affected_in_registered_cohort']==1
    assert report['rows']['fact_recall'][44]['missing']['steered']==1
    assert report['rows']['fact_recall'][44]['missing']['random']==0
    assert report['rules']['R-AR2']==primary['rules']['R-AR2']

def test_redaction_outside_flipped_cohort():
    from .sensitivity import sensitivity
    data=fixture();old=dict.fromkeys(a.ROWS,.1);primary=a.analyze(data,old)
    report=sensitivity(data,primary,old,[dict(row='language_plan',layer=52,condition='random',item_id='t80')])
    assert report['affected_readouts']==1 and report['affected_in_registered_cohort']==0
    assert report['rows']['language_plan'][52]['difference']==primary['rows']['language_plan'][52]['oracle']['difference']

def test_redaction_invalid_mapping_rejected():
    from .sensitivity import sensitivity
    data=fixture();old=dict.fromkeys(a.ROWS,.1);primary=a.analyze(data,old)
    record=dict(row='fact_recall',layer=48,condition='steered',item_id='t0')
    with pytest.raises(ValueError):sensitivity(data,primary,old,[record])
    record['layer']=44
    with pytest.raises(ValueError):sensitivity(data,primary,old,[record,record])


@pytest.mark.parametrize('ci,status', [([-.10,.50],'NOT MET'),([0,.50],'NOT MET'),([.01,.50],'MET'),(None,'NOT EVALUABLE')])
def test_rq_falsifier_requires_positive_new44_lower_bound(ci,status):
    # R-Q6f1a233c1: probe .70 and estimate .30 cannot override CI crossing zero.
    p={r:{l:.70 for l in a.LAYERS} for r in a.ROWS}
    s={r:{l:dict(estimate=.30,CI95=[.01,.50]) for l in a.READS} for r in a.ROWS}
    for r in a.ROWS:s[r][44]['CI95']=ci
    result=a.classify_rules(p,s,dict.fromkeys(a.ROWS,.10))
    assert result['falsifier']['status']==status
    assert all(result['per_row'][r]['falsifier']['status']==status for r in a.ROWS)
