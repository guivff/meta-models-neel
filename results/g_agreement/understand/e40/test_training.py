"""Synthetic CPU checks for registered E40 calibration, exclusions and single pass."""
import os
import sys
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from calibration import calibrate,eligible,norms64,FilteredGate,seal_calibration
from pipeline import collect_calibration,eligible_batches,evaluate_gate
from e40_sae import Trainer,ScaledSAE,FIXED_CONFIG
from e40_data import chunks,manifest_order
from e40_clock import Clock,NoFit
from worker import memory_admission,claim


def config():
    return replace(FIXED_CONFIG,d_model=2,d_sae=8,k=2,auxiliary_k=4,
                   batch_size=4,target_tokens=10,dead_after_tokens=4)

def test_calibration_order_median_before_outlier_removal_and_fixed_scale():
    x=calibrate([1,2,3,4,100],d_model=2,expected=5)
    assert x['median_raw_norm']==3 and x['outlier_threshold_raw_norm']==30
    assert x['mean_raw_norm_after_outlier_exclusion']==2.5
    assert x['scale']==np.sqrt(2)/2.5
    assert x['calibration_outliers']==1 and not x['heldout_statistics_used']
    np.testing.assert_array_equal(eligible([30,30.001,1],[1,2,0],x),[True,False,False])

@pytest.mark.parametrize('values', [[0,0],[1,np.nan],[1,np.inf],[-1,2]])
def test_invalid_calibration_stops(values):
    with pytest.raises(ValueError):calibrate(values,expected=2,d_model=2)


def test_norms_are_raw_float64():
    x=np.array([[3,4],[0,0]],dtype=np.float32)
    np.testing.assert_array_equal(norms64(x),[5,0])


def test_calibration_seals_before_training_and_refuses_overwrite(tmp_path):
    r=calibrate([1.,2.],expected=2,d_model=2)
    seal_calibration(tmp_path,r)
    assert (tmp_path/'CALIBRATION_SEAL.json').exists()
    with pytest.raises(FileExistsError):seal_calibration(tmp_path,r)


def test_document_positions_continue_across_context_chunks_and_no_replay():
    result=list(chunks([{'source_id':'a','ids':list(range(7))}],length=3))
    assert [r['positions'].tolist()for r in result]==[[0,1,2],[3,4,5],[6]]
    with pytest.raises(ValueError):list(chunks([{'source_id':'a','ids':[1]}]*2))


def test_section79_uses_manifest_order_and_excludes_groups():
    from e40_common import is_heldout
    allowed=next(str(i)for i in range(100)if not is_heldout(str(i)))
    held=next(str(i)for i in range(100)if is_heldout(str(i)))
    rows=[{'id':'b','group_id':allowed},{'id':'a','group_id':allowed},{'id':'c','group_id':held}]
    result=manifest_order(rows,{'documents':[{'id':'a'},{'id':'c'},{'id':'b'}]})
    assert [r['id']for r in result]==['a','b']


def test_calibration_prefix_rejoins_single_pass_without_re_capture_or_loss():
    calls=[]
    def stream():
        for start in (0,4,8,12):
            calls.append(start)
            x=torch.tensor([[float(i+1),1.]for i in range(start,start+4)])
            pos=np.arange(start,start+4)
            yield x,pos,norms64(x.numpy())
    source=iter(stream())
    b,n,pending=collect_calibration(source,count=5,d_model=2)
    assert calls==[0,4]
    assert b[:,0].tolist()==[2,3,4,5,6]
    c=calibrate(n,d_model=2,expected=5)
    progress={'norm_excluded':0,'untrained_eligible_tail':0}
    rows=[]
    for batch in eligible_batches(b,n,pending,source,c,progress,target=10,batch_size=4):
        rows.append(batch.clone())
    assert [len(x)for x in rows]==[4,4,2]
    assert torch.cat(rows)[:,0].tolist()==list(range(2,12))
    assert calls==[0,4,8] and progress['untrained_eligible_tail']==1


def test_outliers_excluded_before_batch_accounting():
    b=torch.tensor([[1.,0.],[2.,0.],[50.,0.],[3.,0.],[4.,0.]])
    n=norms64(b.numpy());c=calibrate(n,d_model=2,expected=5)
    progress={'norm_excluded':0,'untrained_eligible_tail':0}
    result=[x.clone()for x in eligible_batches(b,n,None,iter(()),c,progress,target=4,batch_size=3)]
    assert [len(x)for x in result]==[3,1]
    assert torch.cat(result)[:,0].tolist()==[1,2,3,4]
    assert progress['norm_excluded']==1


def test_incomplete_source_cannot_train_partial_target():
    b=torch.tensor([[1.,0.],[2.,0.]])
    n=norms64(b.numpy());c=calibrate(n,d_model=2,expected=2)
    with pytest.raises(ValueError):
        list(eligible_batches(b,n,None,iter(()),c,{'norm_excluded':0,'untrained_eligible_tail':0},target=3,batch_size=2))


def test_scaled_checkpoint_roundtrip_and_fresh_actual_initialization():
    c=config();scale=1.75
    scratch=Trainer(scale=scale,device='cpu',config=c,synthetic=True,timing_force_auxiliary=True)
    x=torch.tensor([[1.,2.],[2.,-1.],[3.,1.],[-2.,3.]])
    scratch.step(x,first_position=0,split='train')
    with pytest.raises(ValueError):scratch.checkpoint_tensors()
    a=Trainer(scale=scale,device='cpu',config=c,synthetic=True)
    b=Trainer(scale=scale,device='cpu',config=c,synthetic=True)
    for name in ('W_enc','W_dec','b_enc','b_dec'):
        torch.testing.assert_close(getattr(a.model,name),getattr(b.model,name))
    for size in(4,4,2):
        a.step(x[:size],first_position=a.tokens_seen,split='train')
    params=a.checkpoint_tensors();sae=ScaledSAE(params,scale,k=2)
    with torch.inference_mode():
        torch.testing.assert_close(sae.encode(x),a.model.encode(x*scale))
        torch.testing.assert_close(sae.decode(sae.encode(x)),a.model.decode(a.model.encode(x*scale))/scale)
    assert a.completed_manifest()['experiment']=='E40'
    assert a.tokens_seen==10 and a.steps==3

@pytest.mark.parametrize('kwargs',[{'config':config()},{'timing_force_auxiliary':True}])
def test_production_cannot_change_registered_config_or_force_auxiliary(kwargs):
    with pytest.raises(ValueError):Trainer(scale=1,device='cpu',**kwargs)


def test_filtered_gate_keeps_same_thresholds_without_50000_size_requirement():
    x=np.array([[1.],[3.]])
    z=np.ones((2,10))
    a=FilteredGate(1,10);a.update(x,x+.5,codes=z)
    r=a.result();assert r['fvu']==.25 and r['passed']
    z[:,0]=0
    b=FilteredGate(1,10);b.update(x,x,codes=z)
    assert b.result()['dead_fraction']==.1 and not b.result()['passed']


def test_gate_reports_filtered_and_all_from_same_codes_and_raw_units():
    class Identity:
        d_model=1;d_sae=2
        def encode(self,x):return torch.cat((x,torch.ones_like(x)),dim=1)
        def decode(self,z):return z[:,:1]
    class C:
        def check(self):pass
    h=np.array([[100.],[1.],[2.],[3.]],dtype=np.float32)
    cal={'outlier_threshold_raw_norm':10}
    r=evaluate_gate(Identity(),h,np.array([0,1,2,3]),cal,C(),expected=4,batch_size=2,device='cpu')
    assert r['filtered']['n_tokens']==3 and r['filtered']['fvu']==0
    assert r['all_tokens']['n_tokens']==4 and r['all_tokens']['fvu']==0
    assert r['excluded']=={'position_zero':1,'norm_above_threshold':1,'overlap':1,'union':1}


def assignment():
    return {'issuer':'integrator','experiment':'E40','stage':'training','gpu_count':1,'pod_id':'test',
        'request_sha256':'a'*64,'source_commit':'b'*40,'source_pushed':True,
        'external_hardstop_verified':True,'hold_renewer_verified':True,
        'provider_created_epoch':1000,'deadline_epoch':47800,'setup_deadline_epoch':2000,
        'previous_gpu_seconds':0,'allocated_gpu_seconds':46800,'later_reserved_gpu_seconds':3600}


def test_clock_full_budget_and_terminal_no_fit(monkeypatch):
    import e40_clock as module
    monkeypatch.setenv('RUNPOD_POD_ID','test');monkeypatch.setattr(module.time,'time',lambda:1100.)
    c=Clock(assignment(),'a'*64);c.begin()
    c.admit(calibration_elapsed=200,calibration_chunks=2000,calibration_retained=999000,
            full_chunk_seconds=[.1]*3,optimizer_seconds=[.1]*3,evaluation_seconds=[.1]*3)
    assert c.forecast_components['optimizer_steps']==24415
    assert c.a['allocated_gpu_seconds']+c.a['later_reserved_gpu_seconds']==50400
    with pytest.raises(ValueError):c.begin()
    monkeypatch.setattr(module.time,'time',lambda:47801.)
    with pytest.raises(NoFit):c.check()
    with pytest.raises(NoFit):c.check()

@pytest.mark.parametrize('field,value',[('previous_gpu_seconds',1),('gpu_count',2),('allocated_gpu_seconds',50400),('later_reserved_gpu_seconds',-1),('source_pushed',False)])
def test_clock_rejects_budget_or_assignment_changes(monkeypatch,field,value):
    monkeypatch.setenv('RUNPOD_POD_ID','test');a=assignment();a[field]=value
    with pytest.raises(ValueError):Clock(a,'a'*64,now=1100)

@pytest.mark.parametrize('free,total,host',[(59e9,141e9,64e9),(70e9,80e9,64e9),(70e9,141e9,47e9)])
def test_large_sae_and_calibration_memory_are_admitted_before_allocating(free,total,host):
    with pytest.raises(ValueError):memory_admission(free,total,host)


def test_valid_memory_admission():
    r=memory_admission(70e9,141e9,64e9)
    assert r['calibration_host_buffer_bytes']==20480000000


def test_full_fourteen_hour_assignment_is_allowed_without_invented_stage_cut(monkeypatch):
    monkeypatch.setenv('RUNPOD_POD_ID','test')
    a=assignment();a.update(allocated_gpu_seconds=50400,later_reserved_gpu_seconds=0,deadline_epoch=51400)
    c=Clock(a,'a'*64,now=1100)
    assert c.a['allocated_gpu_seconds']==50400


def test_decomposition_uses_same_scaled_encoder_and_raw_decoder_norms():
    from decomposition import encode_triplet
    c=config();trainer=Trainer(scale=2,device='cpu',config=c,synthetic=True)
    sae=ScaledSAE({name:getattr(trainer.model,name).detach().clone()for name in('W_enc','W_dec','b_enc','b_dec')},2,k=2)
    h=torch.tensor([[1.,2.],[2.,3.]])
    win=h*.3;ol=h*.1
    result=encode_triplet(sae,h,win,ol,authorized=True)
    index,value=result['window_loss'];dense=np.zeros((2,8));np.put_along_axis(dense,index,value,axis=1)
    np.testing.assert_allclose(dense,sae.core.encode((h-win)*2).numpy(),rtol=1e-6)
    np.testing.assert_allclose(sae.raw_decoder_norms(),np.linalg.norm(sae.core.W_dec.numpy().astype(np.float64),axis=0)/2)

@pytest.mark.parametrize('changed',['torch','transformers','triton','fla-core','tokenizers'])
def test_forward_runtime_drift_is_an_operational_setup_stop(changed):
    from worker import validate_runtime,RUNTIME_FILE,ROOT,OperationalSetupError
    import json
    versions=json.loads((ROOT/RUNTIME_FILE).read_text())
    validate_runtime(versions)
    versions[changed]='different'
    with pytest.raises(OperationalSetupError):validate_runtime(versions)
