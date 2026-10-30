from pathlib import Path
import numpy as np
import pytest
from projects.g_agreement.e112_runner.build import transform,selection,payload,ROOT


def test_site_centred_rank1_only_no_norm_rescaling():
    h=np.array([[2,3,8],[4,7,10],[9,11,12]],np.float32);q=np.array([[1.],[0],[0]])
    y,mu,diagnostics=transform(h,q)
    assert y.dtype==np.float32 and np.all(y[:,0]==np.float32(h[:,0].mean(dtype=np.float64)))
    assert np.array_equal(y[:,1:],h[:,1:]) and np.allclose(mu,h.mean(axis=0,dtype=np.float64))
    assert len(diagnostics['norm_ratios'])==3 and diagnostics['variance_removed']>0
    shifted=h+np.array([10,20,30],np.float32)
    other,mu2,_=transform(shifted,q)
    assert np.allclose(other-y,[10,20,30]) and not np.array_equal(mu,mu2)


def test_frozen_k_file_cannot_be_substituted(tmp_path):
    assert selection(ROOT/'results/g_agreement/understand/e112/K_SELECTION.json')['k']==1
    p=tmp_path/'wrong.json';p.write_text('{"k":2}')
    with pytest.raises(ValueError):selection(p)


def test_worker_diff_is_only_registered_single_condition_variant():
    old=payload()['results/g_agreement/understand/e80c/worker80c.py'].decode()
    expected=old.replace('E80c','E112').replace('three new conditions','one new PCA-1 condition').replace("CONDITIONS=('J_ablated','random_ablated','PCA_ablated')","CONDITIONS=('PCA1_ablated',)").replace('all three new conditions','single frozen PCA-1 condition').replace('count=65*3','count=65').replace('oracle=1554,nla=1554','oracle=518,nla=518').replace('3x518x2 outputs','1x518x2 outputs').replace('new_readouts=3108','new_readouts=1036').replace('from test_worker80c import Tiny80c','from test_worker112 import Tiny80c')
    assert (ROOT/'results/g_agreement/understand/e112/worker112.py').read_text()==expected


def test_admission_bind_only_changes_request_and_preserves_vector_bytes(tmp_path):
    from projects.g_agreement.e112_runner.build import bind_stage,sha,write,read
    source=tmp_path/'original';source.mkdir()
    (source/'PCA1_ablated44.npy').write_bytes(b'unchanged sealed vector bytes')
    write(source/'STAGE_REQUEST.json',dict(experiment='E112',status='HOLD_INTEGRATOR_ADMISSION',seed_seconds_per_batch={}))
    write(source/'INPUT_SEAL.json',dict(files={p.name:sha(p) for p in source.iterdir()}))
    digest=sha(source/'INPUT_SEAL.json');out=tmp_path/'bound'
    result=bind_stage(source,digest,out,3000,3000,900)
    assert result['vector_bytes_unchanged'] and sha(out/'PCA1_ablated44.npy')==sha(source/'PCA1_ablated44.npy')
    assert read(out/'STAGE_REQUEST.json')['status']=='READY' and read(source/'STAGE_REQUEST.json')['status'].startswith('HOLD')
    assert sha(source/'INPUT_SEAL.json')==digest
