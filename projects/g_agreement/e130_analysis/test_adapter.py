"""Synthetic source admission and scientific kernel checks; no real E130 inputs."""
import ast
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
import torch
from . import kernel as k
from . import run_once as r


def toy():
    rng = np.random.default_rng(8)
    y = np.tile([0,1,0,1],10)
    x = rng.normal(0,.05,(40,6)).astype(np.float32)
    x[:,0] += 2*y-1
    return x,y,np.repeat(np.arange(10),4)


def test_grouped_folds_keep_quartets_and_cover_once():
    x,y,g = toy()
    folds = k.group_folds(g)
    assert sorted(np.concatenate(folds).tolist()) == list(range(40))
    for te in folds:
        assert set(g[te]).isdisjoint(set(g[np.setdiff1d(np.arange(40),te)]))
    pred,_ = k.cv(x,y,g)
    assert k.roc_auc_score(y,pred) == 1


def test_frozen_probe_not_condition_standardized_or_reoriented():
    x,y,g = toy(); m = k.fit(x,y)
    assert k.roc_auc_score(y,k.score(m,x)) == 1
    assert k.roc_auc_score(y,k.score(m,-x)) == 0
    assert torch.allclose(m.sd,torch.as_tensor(x).std(0).clamp_min(1e-4))
    shifted = x+3
    assert np.allclose(k.score(m,shifted),((shifted-m.mu.numpy())/m.sd.numpy())@m.w.numpy()+m.b)


def test_bootstrap_is_paired_and_never_refits():
    y=np.array([0,0,1,1]); p=dict(intact=y,shuffled=1-y)
    with patch.object(k,'fit',side_effect=AssertionError('bootstrap fit')):
        a=k.summary(y,p,draws=100)
    assert a['intact_minus_shuffle'] == dict(delta=1.,CI95=[1.,1.])
    assert a['bootstrap']['undefined_single_class'] > 0
    assert a['bootstrap']['valid']+a['bootstrap']['undefined_single_class'] == 100
    assert a == k.summary(y,p,draws=100)


@pytest.mark.parametrize('control,auc,lower,delta,want',[
    (.799,1.,.9,.5,'UNINFORMATIVE_TRUE_SPAN_CONTROL_BELOW_0.80'),
    (.8,.7,.6001,.1,'CARRIED_IN_READOUT_ARRANGEMENT'),
    (1.,.7,.6,.1,'INCONCLUSIVE'),
    (1.,.6,.5,.3,'NOT_CARRIED_UNDER_E130_PROTOCOL'),
    (1.,.75,.65,.099,'INCONCLUSIVE')])
def test_registered_boundaries(control,auc,lower,delta,want):
    z=dict(scores=dict(intact=dict(AUROC=auc,CI95=[lower,1.])),intact_minus_shuffle=dict(delta=delta))
    assert k.reading(control,z) == want


def labels():
    rows=[]; order={'dev':[],'test':[]}
    for group in range(150):
        split='dev' if group<50 else 'test'
        for genre in (0,1):
            for addressed in (0,1):
                i=f'{group}:{genre}:{addressed}'
                order[split].append(i)
                rows.append(dict(public_id=i,split=split,matched_set=group,genre=genre,addressed=addressed))
    return order,rows


def test_original_label_groups_are_not_guessed():
    order,rows=labels(); bound=k.label_binding(order,rows)
    assert len(np.unique(bound['dev']['groups'])) == 50
    rows[0]['matched_set']=149
    with pytest.raises(ValueError,match='split-disjoint'):
        k.label_binding(order,rows)


def synthetic_index():
    order,lab=labels(); rows=[]; tokens=[]; dev=[]
    import random
    rng=random.Random(20261031)
    for c,split in [('span_32','dev'),('ol_readout','test'),('ol_readout_shuffled','test')]:
        for j,i in enumerate(order[split]):
            rows.append(dict(id=i,condition=c,split=split,file=c+'.npy',index=j))
    for i in order['dev']:
        ids=list(range(32)); dev.append(dict(id=i,ids=ids))
        tokens.append(dict(id=i,condition='span_32',split='dev',ids=ids))
    for i in order['test']:
        ids=[10,11,12]; shuffled=list(ids)
        for _ in range(10):
            rng.shuffle(shuffled)
            if shuffled != ids:break
        for c,ts in [('ol_readout',ids),('ol_readout_shuffled',shuffled)]:
            tokens.append(dict(id=i,condition=c,split='test',ids=ts))
    return order,rows,tokens,dev


def test_exact_complete_index_and_token_shuffle():
    order,rows,tokens,dev=synthetic_index()
    r.index_check(rows,order);r.tokens_check(tokens,order,dev)
    tokens[-1]['ids']=[99]
    with pytest.raises(ValueError,match='shuffle'):
        r.tokens_check(tokens,order,dev)


def test_missing_and_duplicate_and_mixed_batches_rejected():
    order,rows,tokens,dev=synthetic_index()
    with pytest.raises(ValueError,match='1000'):
        r.index_check(rows[:-1],order)
    rows[-1]['file']=rows[0]['file']; rows[-1]['index']=200
    with pytest.raises(ValueError,match='unmixed'):
        r.index_check(rows,order)


def test_atomic_guard_never_resets(tmp_path):
    p=tmp_path/'ONCE.json';r.claim(p,dict(a=1))
    with pytest.raises(FileExistsError):r.claim(p,dict(a=2))
    assert r.read(p)==dict(a=1)
    assert 'e125' not in str(r.GUARD).lower()


def test_tampered_seal_rejected_without_numpy_open(tmp_path):
    r.write(tmp_path/'x.json',dict(x=1))
    r.write(tmp_path/'seal.json',dict(files={'x.json':r.sha(tmp_path/'x.json')}))
    digest=r.sha(tmp_path/'seal.json');r.write(tmp_path/'x.json',dict(x=2))
    with patch.object(np,'load',side_effect=AssertionError('array opened')):
        with pytest.raises(ValueError,match='sealed member'):
            r.verified_seal(tmp_path,'seal.json',digest)


def test_degenerate_cv_fails_explicitly():
    x,y,g=toy()
    with pytest.raises(ValueError,match='five original groups'):
        k.cv(x,y,np.zeros(40))


def test_outer_transport_binds_inner_without_array_open(tmp_path):
    inner=tmp_path/'acq';inner.mkdir()
    r.write(inner/'OUTPUT_SEAL.json',dict(status='COMPLETE'))
    pin=dict(path=str(inner/'OUTPUT_SEAL.json'),sha256=r.sha(inner/'OUTPUT_SEAL.json'))
    outer=dict(experiment='E130',status='COMPLETE',source_sha256=r.RUNNER_SHA,
               input_sha256=r.INPUT_SHA,outputs_unopened=True,inner_seal='acq/OUTPUT_SEAL.json',
               files={'acq/OUTPUT_SEAL.json':pin['sha256']})
    r.write(tmp_path/'OUTPUT_SEAL.json',outer)
    op=dict(path=str(tmp_path/'OUTPUT_SEAL.json'),sha256=r.sha(tmp_path/'OUTPUT_SEAL.json'))
    with patch.object(np,'load',side_effect=AssertionError('array opened')):
        r.verified_outer(op,pin)
        with pytest.raises(ValueError,match='inner seal lineage'):
            r.verified_outer(op,dict(path=str(tmp_path/'different'),sha256=pin['sha256']))
        outer['files']['../escape']='0'*64
        r.write(tmp_path/'OUTPUT_SEAL.json',outer);op['sha256']=r.sha(tmp_path/'OUTPUT_SEAL.json')
        with pytest.raises(ValueError,match='transport member'):
            r.verified_outer(op,pin)
