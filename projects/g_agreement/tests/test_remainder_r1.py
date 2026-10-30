"""Detector arithmetic, covariance control, coverage, and sampling regression tests."""
import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r1 as R


def test_identical_states_are_chance_and_difference_zero():
    x=np.arange(40.)
    v=R.detection_stats(x,x)[0]
    assert v[0]==pytest.approx(.5)
    assert v[1]==pytest.approx(.05)
    assert v[3]==0
    assert v[4]==0


def test_signal_detected_and_threshold_never_exceeds_five_percent():
    for n in [16,20,32,40,196]:
        x=np.arange(float(n))
        v=R.detection_stats(x,x+n)[0]
        assert v[0]==1
        assert v[1]==1
        assert v[2]<=.05


def test_ties_do_not_create_false_positives():
    v=R.detection_stats(np.ones(32),np.ones(32))[0]
    assert v[0]==.5
    assert v[1]==0
    assert v[2]==0


def test_content_and_detection_are_paired_but_distinct():
    x=np.arange(32.);labels=np.tile([0,1],16);content=-labels.astype(float)
    v=R.detection_stats(x,x+100,content,labels)[0]
    assert v[0]==1
    assert v[5]==0
    assert v[6]==1


def test_vectorized_bootstrap_matches_scalar():
    rng=np.random.default_rng(123);x=rng.normal(size=(7,30));e=rng.normal(size=(7,30))
    got=R.detection_stats(x,e)
    for j in range(7):np.testing.assert_allclose(got[j,:5],R.detection_stats(x[j],e[j])[0,:5])


def test_woodbury_mahalanobis_matches_full_covariance():
    rng=np.random.default_rng(4);pool=rng.normal(size=(20,7));h=rng.normal(size=(8,7));g=R.PoolGeometry(pool)
    cov=np.cov(pool,rowvar=False)+g.lam*np.eye(pool.shape[1]);z=h-pool.mean(0)
    expected=np.sqrt(np.einsum('ij,jk,ik->i',z,np.linalg.inv(cov),z))
    np.testing.assert_allclose(g.score(h)['mahalanobis'],expected,rtol=1e-10)


def test_knn_and_j_energy_reference():
    pool=np.arange(30.).reshape(10,3);h=np.array([[1.,2.,3.],[4.,5.,6.]])
    got=R.PoolGeometry(pool).score(h,np.eye(3)[:,:2])
    distances=np.linalg.norm(h[:,None,:]-pool[None,:,:],axis=-1)
    np.testing.assert_allclose(got['knn'],np.sort(distances,axis=1)[:,:5].mean(1))
    np.testing.assert_allclose(got['j_energy'],(h[:,:2]**2).sum(1)/(h*h).sum(1))


def test_smoke_fails_loudly_for_missing_arm():
    with pytest.raises(RuntimeError,match='SMOKE FAILED: missing'):
        R.require_coverage({('natural',0)}, {('natural',0),('probe',1)})
    R.require_coverage({('natural',0),('probe',1)}, {('natural',0),('probe',1)})


def test_corpus_mapping_and_direction_control():
    assert R.corpus('21_headline_istrump')==R.corpus('24_headline_isiran')
    assert R.corpus('133_context_type_Causality')==R.corpus('135_context_type_Event_duration')
    assert R.direction_group('d_rand9_L38')=='random'
    assert R.direction_group('d_olens_L38')=='Oracle_gradient'


def test_natural_specificity_not_relabelled_signal():
    auc,fpr=R.specificity(np.arange(200.),reps=1000,key='test')
    assert abs(auc-.5)<.02
    assert .03<fpr<.08


def test_r5_audit_rejects_partial_directory_and_misaligned_index(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(R, 'CACHE', tmp_path)
    root = tmp_path/'r5/readback/fact'
    root.mkdir(parents=True)
    selection = {'fact': {'item_ids': ['a', 'b']}}
    conditions = [('natural', 0.), ('d_cm_L38', 1.)]
    assert len(R.r5_readback_audit(selection, conditions)) == 2
    (root/'index.json').write_text(json.dumps({'item_ids': ['a','b'], 'read_layer':42}))
    np.save(root/'natural_a0.0.npy', np.ones((2,3)))
    assert len(R.r5_readback_audit(selection, conditions)) == 1
    np.save(root/'d_cm_L38_a1.0.npy', np.ones((2,3)))
    assert R.r5_readback_audit(selection, conditions) == []
    (root/'index.json').write_text(json.dumps({'item_ids': ['a','a'], 'read_layer':42}))
    with pytest.raises(RuntimeError, match='invalid R5'): R.r5_readback_audit(selection, conditions)


def test_completion_rows_cannot_replace_measured_model_lo(tmp_path):
    import json
    key = 'poetry|item|24|d_swap'
    model = {'key': key, 'part': 'poetry', 'lo_rhyme': 2.5}
    completion = {'key': key, 'part': 'poetry', 'completion': 'fly.'}
    m = tmp_path/'model.jsonl'; c = tmp_path/'completions.jsonl'
    m.write_text(json.dumps(model)+'\n'); c.write_text(json.dumps(completion)+'\n')
    assert R.load_swap_model_rows(m,c) == [model]
    assert R.load_swap_model_rows(c,m) == [model]
    assert R.load_swap_model_rows(c) == []


def test_model_rows_need_all_pair_log_odds_and_unique_crossfile_keys(tmp_path):
    import json
    a = tmp_path/'a.jsonl'; b = tmp_path/'b.jsonl'
    row = {'key': 'khop|item|24|d_swap', 'part': 'khop', 'lo_bridge': 1.0}
    a.write_text(json.dumps(row)+'\n')
    with pytest.raises(ValueError,match='missing/nonfinite model LO'):
        R.load_swap_model_rows(a)
    row['lo_answer'] = 2.0
    a.write_text(json.dumps(row)+'\n'); b.write_text(json.dumps(row)+'\n')
    with pytest.raises(ValueError,match='duplicate model-LO key across sources'):
        R.load_swap_model_rows(a,b)


def test_poetry_reader_rows_keep_their_corpus_identity():
    model = [
        {'part':'poetry','item':'item','layer':None,'arm':'natural','lo_rhyme':2.},
        {'part':'poetry','item':'item','layer':24,'arm':'d_swap','lo_rhyme':-2.},
    ]
    common = {'part':'poetry','item':'item','reader':'jlens','pair':'rhyme'}
    readers = [common|{'layer':None,'arm':'natural','lo':1.},
               common|{'layer':24,'arm':'d_swap','lo':-1.}]
    cells = R.confidence_cells([],[],model,readers)
    assert len(cells)==3
    assert all(cell.dataset=='x27_wsb_poetry' and cell.pair=='rhyme' for cell in cells)
