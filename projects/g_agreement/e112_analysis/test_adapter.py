import copy
import pytest
from . import adapter as a

def fixture():
    return [dict(id=str(i),family='one' if i%2 else 'two',cells={r:dict(none=i<184,J=i>=106,random=i>=40,PCA_k=i>=50) for r in ('oracle','nla')}) for i in range(518)]

def test_registered_paired_effect():
    z=a.analyze(fixture());assert z['R_X5']=='MET' and z['falsifier']=='NOT MET'
    p=z['readers']['oracle']['pooled'];assert p['J_minus_PCA_k']['estimate']==pytest.approx(56/184)
    assert z['sealed_J_fall']==pytest.approx(106/184)
    assert sum(x['n'] for x in z['readers']['oracle']['per_family'].values())==184

def test_falsifier_tie():
    rows=fixture()
    for x in rows:x['cells']['oracle']['PCA_k']=x['cells']['oracle']['J']
    z=a.analyze(rows);assert z['R_X5']=='NOT MET' and z['falsifier']=='MET'
    assert z['readers']['oracle']['pooled']['J_minus_PCA_k']['ci95']==[0,0]

def test_pairing_and_seed():
    xs=[dict(J=False,PCA_k=True)]*10+[dict(J=True,PCA_k=False)]*10
    assert a.paired(xs)==a.paired(xs)
    assert a.paired(xs)['J_minus_PCA_k']['ci95'][0]<0
    assert a.paired([dict(J=False,PCA_k=False)]*20)['J_minus_PCA_k']['ci95']==[0,0]

def test_missing_not_failure_or_new_cohort():
    rows=fixture();rows[0]['cells']['oracle']['PCA_k']=None
    z=a.analyze(rows);assert z['R_X5']=='NOT EVALUABLE' and z['falsifier']=='NOT EVALUABLE'
    assert z['readers']['oracle']['pooled']['n_missing']==1
    assert z['readers']['oracle']['pooled']['n']==184

def test_cohort_and_original_j_are_frozen():
    for kind in ('none','J'):
        rows=fixture();rows[0]['cells']['oracle'][kind]=not rows[0]['cells']['oracle'][kind]
        with pytest.raises(ValueError):a.analyze(rows)
    with pytest.raises(ValueError):a.analyze(fixture()[:-1])

def test_nla_is_exploratory_same_fixed_cohort():
    rows=fixture()
    for x in rows:x['cells']['nla']['none']=False
    z=a.analyze(rows);assert z['readers']['nla']['role']=='exploratory'
    assert z['readers']['nla']['pooled']['n']==184 and z['R_X5']=='MET'

def test_smallest_k_all518_share():
    p=dict(cumulative_variance=[.10,.15,.30],k=2,J_variance_share=.1431,n=518,basis_block=44,centred=True,same_e80c_mu_and_basis=True)
    assert a.projection(p)==2
    for key,val in [('k',3),('J_variance_share',.173),('n',184)]:
        q=copy.deepcopy(p);q[key]=val
        with pytest.raises(ValueError):a.projection(q)

def test_empty_small_missing():
    assert a.paired([])['R_X5']=='NOT EVALUABLE'
    assert a.paired([dict(J=False,PCA_k=None)])['n_complete']==0
    assert a.paired([dict(J=False,PCA_k=True)])['R_X5']=='NOT EVALUABLE'

def test_tamper_once(tmp_path):
    a.core.write(tmp_path/'x.json',{});a.core.seal(tmp_path,'SEAL.json');h=a.core.sha(tmp_path/'SEAL.json')
    (tmp_path/'x.json').write_text('tampered')
    with pytest.raises(ValueError):a.core.verify(tmp_path/'SEAL.json',h)
    s=dict(analysis=str(tmp_path/'out'),guard=str(tmp_path/'guard'),output_sha256='synthetic');a.core.claim(s,'synthetic')
    s['analysis']=str(tmp_path/'again')
    with pytest.raises(FileExistsError):a.core.claim(s,'synthetic')


def test_ruling_requires_real_current_verification_and_r5(tmp_path,monkeypatch):
    import json
    from projects.g_agreement.e112_analysis import adapter as a
    def write(name,value):
        p=tmp_path/name;p.write_text(json.dumps(value));return a.core.sha(p)
    ih=write('INVENTORY.json',{});ph=write('PROVENANCE.json',{});pr=write('PROJECTION.json',{})
    sh=write('SEAL.json',dict(files={'INVENTORY.json':ih,'PROVENANCE.json':ph,'PROJECTION.json':pr}))
    review=dict(files={'PROVENANCE.json':ph},reviewer='R-5',status='PROVENANCE_VERIFIED',inventory_sha256=ih,provenance_sha256=ph,projection_sha256=pr)
    rh=write('REVIEW.json',review)
    proof={k:dict(ok=True) for k in ('route','privacy','labels_cpu_only','source_order','pre_output_commits')};proof['inventory']=dict(seal=sh,inventory=ih,provenance=ph)
    s=dict(trackq_verification=proof,source_seals=[dict(seal=str(tmp_path/'SEAL.json'),sha256=sh)],inventory=dict(seal_index=0),projection=dict(seal_index=0,member='PROJECTION.json'),r5_review_seal=str(tmp_path/'REVIEW.json'),r5_review_sha256=rh)
    inv=dict(experiment='E112',pre_output='MISSING');a.ruling_admission(s,inv)
    assert inv['pre_output']=='MISSING'
    proof['privacy']['ok']=False
    import pytest
    with pytest.raises(ValueError):a.ruling_admission(s,inv)
