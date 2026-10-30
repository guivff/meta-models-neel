import copy
import pytest
import numpy as np
from . import rules as r
from . import adapter as a

def selected(alpha=1.):
    d={}
    for arm in r.ARMS:
        for row in r.ROWS:
            grid=(.5,1.,2.,4.,8.) if arm=='U' else (.5,1.,2.,4.)
            d[f'{arm}:{row}']=dict(alpha=alpha,target_side_counts={str(x):60 if alpha is not None and x>=alpha else 0 for x in grid})
    return d

def fixture():
    return [dict(id=f'{arm}:{row}:{i}:{c}',item_id=str(i),arm=arm,row=row,condition=c,score=1 if c=='steered' else 0,flipped=c=='steered',norm_ratio=1. if arm=='N' else 2.,read_norm_ratio=1.2) for arm in r.ARMS for row in r.ROWS for i in range(84) for c in ('steered','random')]

def test_both_arm_rules_and_norms():
    out=r.analyze(fixture(),selected())
    assert out['rules']['R-U1']['status']==out['rules']['R-N1']['status']=='MET'
    assert out['rules']['falsifier']['status']=='NOT MET'
    assert out['arms']['U']['fact_recall']['norms']['steered']['0']['norm_over_1_5']
    assert out['arms']['N']['fact_recall']['B_random']['estimate']==0

def test_same_steered_cohort_and_all_item_rates():
    xs=fixture()
    for x in xs:
        i=int(x['item_id']);x['flipped']=(i<42 if x['condition']=='steered' else i>=42);x['score']=1 if i<42 else -1
    z=r.analyze(xs,selected())['arms']['U']['fact_recall']
    assert z['difference']['CI95']==[0,0] and z['S_random']['estimate']==1
    assert z['S_all_random']['estimate']==0 and z['flipped_n']==42
    assert z['missing']['random']['all_test']==0 and z['excluded_not_flipped']==42

def test_falsifier_requires_every_eligible_cell():
    xs=fixture()
    for x in xs:x['score']=0
    assert r.analyze(xs,selected())['rules']['falsifier']['status']=='MET'
    for x in xs:
        if x['arm']=='N' and x['row']=='fact_recall' and x['condition']=='steered':x['score']=1
    assert r.analyze(xs,selected())['rules']['falsifier']['status']=='NOT MET'

def test_no_eligible_not_vacuously_met():
    out=r.analyze([],selected(None))
    assert all(x['status']=='NOT EVALUABLE' for x in out['rules'].values())
    d=selected();d['U:fact_recall']['alpha']=d['U:language_plan']['alpha']=None
    xs=[x for x in fixture() if x['arm']=='N'];out=r.analyze(xs,d)
    assert out['rules']['R-U1']['status']=='NOT EVALUABLE' and out['rules']['R-N1']['status']=='MET'

def test_missing_counts_distinct_from_cohort_exclusion():
    xs=fixture()
    for x in xs:
        if int(x['item_id'])>=70:x['flipped']=False
        if int(x['item_id'])==0:x['score']=None
    z=r.analyze(xs,selected())['arms']['N']['language_plan']
    assert z['excluded_not_flipped']==14 and z['missing']['steered']['flipped_cohort']==1
    assert z['missing']['steered']['cohort_kept']==69

def test_all_missing_and_empty_flipped_are_unknown():
    xs=fixture()
    for x in xs:x['score']=None
    assert r.analyze(xs,selected())['rules']['R-U1']['status']=='NOT EVALUABLE'
    for x in xs:x['score']=1;x['flipped']=False
    assert r.analyze(xs,selected())['rules']['falsifier']['status']=='NOT EVALUABLE'

def test_dose_grid_and_smallest_passing():
    a.validate_doses(selected())
    d=selected();d['U:fact_recall']=dict(alpha=8.,target_side_counts={str(x):60 if x==8 else 0 for x in (.5,1.,2.,4.,8.)});a.validate_doses(d)
    d['N:fact_recall']=dict(d['U:fact_recall'])
    with pytest.raises(ValueError,match='grid'):a.validate_doses(d)
    d=selected();d['U:fact_recall']['alpha']=2.
    with pytest.raises(ValueError,match='smallest'):a.validate_doses(d)

def test_threshold_edges_and_strict_intervals():
    assert r.threshold({'estimate':.3,'CI95':[.01,.5]},.3) is True
    assert r.threshold({'estimate':.3,'CI95':[0,.5]},.3) is False
    assert r.threshold({'estimate':.1,'CI95':[-.1,.299]},.1,upper=True) is True
    assert r.threshold({'estimate':.1,'CI95':[-.1,.3]},.1,upper=True) is False

def test_shared_backend_reproducible_and_joint():
    values={str(i):(-1 if i%2 else 1) for i in range(84)}
    assert r.statistic(values,values)['CI95']==[0,0]
    assert r.statistic(values)==r.statistic(values)
    assert r.SEED==20261028 and r.DRAWS==2000

def test_source_gate_before_input(monkeypatch):
    monkeypatch.setattr(a,'committed',lambda:(_ for _ in ()).throw(ValueError('uncommitted')))
    monkeypatch.setattr(a,'read',lambda _:pytest.fail('opened before source gate'))
    monkeypatch.setattr('sys.argv',['e104','analyze','--spec','never'])
    with pytest.raises(ValueError,match='uncommitted'):a.main()

def test_full_sealed_input_grid_and_tamper(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir();raw=[];records=[]
    for x in fixture():
        n=len(raw);raw.append(dict(text='synthetic',pair_scores=[[1.,0.]],norm_ratio=x['norm_ratio'],read_norm_ratio=x['read_norm_ratio']))
        meta={k:x[k] for k in ('id','item_id','arm','row','condition')}
        records.append(dict(meta,reader='oracle',split='test',alpha=1.,target='A',values={'A':'a','B':'b'},property=x['row'],contrast_target_sign=1,behaviour_scorer_sha256='synthetic-frozen',candidate_count=1,measurements={f:dict(seal_index=0,member='raw.json',keys=[n,f]) for f in raw[-1]}))
    a.write(source/'raw.json',raw);a.core.seal(source,'SEAL.json',experiment='E104')
    root=tmp_path/'bundle';root.mkdir();a.write(root/'RECORDS.json',records)
    a.core.seal(root,'SEAL.json',experiment='E104',status='COMPLETE',labels_cpu_only=True,dose_sha256='dose',random_seed=20261029,reader='oracle',read_block=44,U_hook=dict(block=40,positions='eight_before_read',read_token_untouched=True),N_hook=dict(block=44,positions='read_token',renormalized=True,random_renormalized=True),source_seals=[dict(seal=str(source/'SEAL.json'),sha256=a.sha(source/'SEAL.json'))])
    monkeypatch.setattr(a,'dose',lambda *args:selected())
    spec=dict(dose_path='unused',dose_commit='unused',dose_sha256='dose',input_seal=str(root/'SEAL.json'),input_sha256=a.sha(root/'SEAL.json'))
    parsed,_=a.inputs(spec);assert len(parsed)==672 and all(x['flipped'] for x in parsed)
    (source/'raw.json').write_text('[]')
    with pytest.raises(ValueError,match='member mismatch'):a.inputs(spec)
