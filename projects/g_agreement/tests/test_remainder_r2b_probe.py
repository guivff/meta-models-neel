import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r2b_probe as P


def test_grouped_fit_and_raw_direction():
    rng=np.random.default_rng(1);y=np.tile([0,1],20);x=rng.normal(0,.1,(40,4));x[:,0]+=y*3
    groups=np.repeat(np.arange(10),4)
    fit=P.fit_pool(x,y,groups,['heldout'])
    score,pred=P.predict(fit,x)
    assert np.array_equal(pred,y) and fit['pool_validation_accuracy']==1
    assert np.isclose(np.linalg.norm(fit['raw_normal']),1)


def test_heldout_group_decoy():
    with pytest.raises(ValueError,match='decoy'):
        P.validate_training(np.ones((4,2)),[0,1,0,1],['a','a','decoy','decoy'],['decoy'])


def test_fixed_transfer_preserves_split_and_has_no_validation_score():
    rng=np.random.default_rng(9);y=np.tile([0,1],10);x=rng.normal(size=(20,3));x[:,0]+=y*4
    fit=P.fit_fixed_transfer(x,y,['pool-component']*20,['test-component'])
    assert fit['C']==1 and fit['pool_validation_accuracy'] is None
    assert fit['selection']=='forward-block transfer'
    with pytest.raises(ValueError,match='decoy'):
        P.fit_fixed_transfer(x,y,['decoy']*20,['decoy'])
