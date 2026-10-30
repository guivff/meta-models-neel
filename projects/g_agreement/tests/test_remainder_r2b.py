import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r2b as R


def test_named_decoy_path(tmp_path):
    with pytest.raises(ValueError, match='decoy.json'):
        R.audit_paths(tmp_path, [tmp_path/'decoy.json'])


def test_named_decoy_arm_and_missing_cell():
    p=R.stamp('fake','abc','a'*64,'test')
    with pytest.raises(ValueError, match='decoy_arm'):
        R.audit_rows([dict(cell=['decoy_arm'], **p)], {('natural',)}, p)
    with pytest.raises(ValueError, match='natural'):
        R.audit_rows([], {('natural',)}, p)


def test_process_decoy_and_uniqueness():
    p=R.stamp('fake','abc','a'*64,'test');q=R.stamp('fake','abc','a'*64,'test')
    assert p['run_id'] != q['run_id']
    with pytest.raises(ValueError, match='run_id'):
        R.audit_rows([dict(cell=['natural'], **q)], {('natural',)}, p)


def test_named_decoy_split():
    with pytest.raises(ValueError, match='decoy_entity'):
        R.audit_split(['decoy_entity'], ['decoy_entity'])


def test_taps_and_depth_decoy():
    assert R.tap_blocks(64)==(16,32,48)
    with pytest.raises(ValueError, match='3'):R.tap_blocks(3)


def test_selection_is_deterministic_balanced_and_excludes_defect():
    facts=[dict(dataset=str(i), label_defect=False,binary=True,provenance_ok=True,median_abs_model_margin=i) for i in range(40)]
    facts.append(dict(dataset='defect', label_defect=True,binary=True,provenance_ok=True,median_abs_model_margin=0))
    a=R.select_main(facts);b=R.select_main(list(reversed(facts)))
    assert a==b and len(a)==20
    assert {i:sum(x['difficulty_bin']==i for x in a) for i in range(5)}==dict.fromkeys(range(5),4)
    assert 'defect' not in {x['dataset'] for x in a}
    with pytest.raises(ValueError,match='difficulty bin'):R.select_main(facts[:10])


def test_mean_ablation_removes_only_pool_centered_normal():
    h=np.array([[3.,4.,5.],[1.,2.,8.]])
    mu=np.array([1.,1.,1.]);u=R.raw_normal([1,2,0],[2,1,1])
    a=R.mean_ablate(h,mu,u)
    assert np.allclose((a-mu)@u,0)
    v=R.random_orthogonal(u,'test')
    assert np.isclose(v@u,0) and np.isclose(np.linalg.norm(v),1)
    assert np.allclose((a-h)@v,0)
    assert np.array_equal(v,R.random_orthogonal(u,'test'))
    with pytest.raises(ValueError,match='unit normal'):R.mean_ablate(h,mu,u*2)


def test_access_requires_equivalence_and_successful_manipulation():
    p=dict(source=.9,internal=.9,constrained=.6,free=.6)
    ci={s:(p[s]-.03,p[s]+.03) for s in R.STAGES}
    assert R.verdict(p,ci,{'access':.01},(-.02,.02),True)=='ACCESS BOTTLENECK'
    assert R.verdict(p,ci,{'access':.01},(-.2,.02),True)=='UNDERPOWERED/MIXED'
    assert R.verdict(p,ci,{'access':.01},(-.02,.02),False)=='UNDERPOWERED/MIXED'
    assert R.verdict(p,ci,{'access':.11},(-.02,.02),True)=='UNDERPOWERED/MIXED'


def test_bh_missing_hypotheses_conservative():
    assert np.allclose(R.bh([.01,.04,1]),[.03,.06,1])
    with pytest.raises(ValueError,match='BH'):R.bh([np.nan])


def test_text_buffer_boundaries():
    assert R.text_buffer_verdict((-.049,.049),(-.06,.06))=='TEXT-LIKE'
    assert R.text_buffer_verdict((-.05,.04),(-.06,.06))=='UNDERPOWERED/MIXED'
    assert R.text_buffer_verdict((.07,.1),(.051,.12))=='STATE-SPECIFIC'
    assert R.text_buffer_verdict((.07,.1),(.05,.12))=='UNDERPOWERED/MIXED'


def test_budget_subset_is_nested_and_stratified():
    facts=[dict(dataset=f'{b}-{i}',difficulty_bin=b) for b in range(5) for i in range(4)]
    full=R.rebuilt_subset(facts,100,100,100,300)
    small=R.rebuilt_subset(list(reversed(facts)),100,5300,100,300)
    assert full['n']==20 and small['n']==15
    assert small['facts']==full['facts'][:15]
    assert all(sum(s.startswith(str(b)+'-') for s in small['facts'])==3 for b in range(5))
    with pytest.raises(ValueError,match='No authorized rebuilt subset fits'):
        R.rebuilt_subset(facts,7000,100,100,300)
    with pytest.raises(ValueError,match='twenty-fact inventory'):
        R.rebuilt_subset(facts+[dict(dataset='decoy',difficulty_bin=0)],100,100,100,300)
