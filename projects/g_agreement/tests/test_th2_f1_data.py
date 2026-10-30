"""Registered data anti-leakage and semantic checks, independent of real outcomes."""
from collections import Counter
import numpy as np
import pandas as pd
from projects.g_agreement.r_bench.th2_f1_data import (
    eligible_facts, select_pool_indices, symmetric_candidate_frequency,
)


def test_pool_excludes_test_documents_across_facts_and_nonfinite_states():
    ids=['own_test','pool_same_doc','pool_clean0','pool_clean1','bad_state']
    bank={
        'own_test':{'split':'test','text_hash':'a','label':0},
        'pool_same_doc':{'split':'pool','text_hash':'a','label':1},
        'pool_clean0':{'split':'pool','text_hash':'b','label':0},
        'pool_clean1':{'split':'pool','text_hash':'c','label':1},
        'bad_state':{'split':'pool','text_hash':'d','label':1},
    }
    found=select_pool_indices(ids,bank,{'a'},[True,True,True,True,False])
    assert found.tolist()==[2,3]
    # Endpoint labels are not consulted by document exclusion.
    bank['own_test']['label']=1
    assert np.array_equal(found,select_pool_indices(ids,bank,{'a'},[True,True,True,True,False]))


def test_candidate_frequency_is_symmetric_and_uses_add_one_vocabulary_mass():
    counts=Counter({1:9,2:4})
    mean,diff=symmetric_candidate_frequency([[1],[2]],counts,7)
    assert np.allclose([mean,diff],[(-np.log(10/20)-np.log(5/20))/2,np.log(2)])
    assert (mean,diff)==symmetric_candidate_frequency([[2],[1]],counts,7)
    unseen=symmetric_candidate_frequency([[8],[9]],counts,7)
    assert np.allclose(unseen,[np.log(20),0])
    assert np.isnan(symmetric_candidate_frequency([[],[2]],counts,7)).all()


def test_eligibility_requires_both_labels_in_both_roles_after_intersection():
    rows=[]
    for ds in ['complete','missing_class']:
        for half in ['calibration','endpoint']:
            for label in [0,1]:
                n=9 if ds=='missing_class' and half=='endpoint' and label==1 else 10
                rows.extend({'dataset':ds,'half':half,'label':label} for _ in range(n))
    assert eligible_facts(pd.DataFrame(rows))=={'complete':True,'missing_class':False}


from pathlib import Path as _GuardPath
from projects.g_agreement.tests import _write_guard as WG
_GUARD_ROOT = _GuardPath(__file__).resolve().parents[3]
_GUARD = WG.ModuleWriteGuard([_GUARD_ROOT / 'results' / 'g_agreement', _GUARD_ROOT / 'cache' / 'g_agreement'])
_write_guard = _GUARD.fixture()

def test_zz_outputs_untouched():
    _GUARD.assert_clean()
