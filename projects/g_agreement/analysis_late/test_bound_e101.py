import pytest
from .run_bound_e101 import merge,REQUIRED

def fixture():
    full={k:'synthetic' for k in REQUIRED};full.update(id='one',flipped=True,contrast=2,norm_ratio=1.2,norm_over_1_5=False)
    thin={k:full[k] for k in REQUIRED};thin.update(opaque_id='opaque',score=1,redacted=False)
    return full,thin

def test_thin_join_rejoins_only_sealed_metadata():
    full,thin=fixture();x=merge([full],[thin])[0]
    assert x['flipped'] is True and x['norm_ratio']==1.2 and x['score']==1
    assert 'flipped' not in thin

def test_reject_target_text_identity_or_norm_mutation():
    for field in ('target','text','id','norm_ratio'):
        full,thin=fixture();thin[field]='different'
        with pytest.raises(ValueError):merge([full],[thin])

def test_missing_duplicate_or_unexpected_private_fields():
    full,thin=fixture()
    with pytest.raises(ValueError):merge([full],[thin,thin])
    with pytest.raises(ValueError):merge([full],[])
    thin['unregistered']='x'
    with pytest.raises(ValueError):merge([full],[thin])
