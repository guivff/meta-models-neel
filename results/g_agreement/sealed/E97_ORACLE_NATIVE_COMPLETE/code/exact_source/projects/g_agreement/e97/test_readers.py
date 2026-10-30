import ast
import inspect
import json
import time
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.e97 import readers as W

def valid_go():
    return dict(experiment='E97',capture_sha256=W.CAPTURE,bank_sha256=W.BANK,forecast_sha256=W.FORECAST,forecast_original_commit=W.FORECAST_COMMIT,forecast_git_verified=True,input_sha256_by_reader={'oracle':'inputs'},forecast_commit_epoch=1,issued_epoch=2,forecast_published_before_GO=True,block42_recapture_sha256='a'*64,recapture_git_verified=True,recapture_published_before_GO=True,recapture_shared_commit='b'*40,recapture_sealed_epoch=1.5)

def test_go_requires_exact_committed_forecast_and_input():
    go=valid_go();W.validate_go(go,'inputs','oracle',3)
    for key,value in [('forecast_git_verified',False),('forecast_sha256','0'*64),('issued_epoch',1),('forecast_published_before_GO',False)]:
        with pytest.raises(ValueError):W.validate_go(dict(go,**{key:value}),'inputs','oracle',3)
    with pytest.raises(ValueError):W.validate_go(go,'different','oracle',3)

def test_full_public_test_inventory_no_labels():
    items=[dict(id=f'{i:024x}',vector_index=i)for i in range(3360)]
    h=np.zeros((3360,5120),dtype=np.float32);W.validate(items,h)
    items[0]['label']='A'
    with pytest.raises(ValueError):W.validate(items,h)

@pytest.mark.parametrize('failure',['generation','no_fit'])
def test_actual_worker_failure_seal_and_retained_pilot(tmp_path,failure):
    tree=ast.parse(inspect.getsource(W.main));guard=next(x for x in tree.body[0].body if isinstance(x,ast.Try))
    class Backend:
        def __init__(self,*a,**k):pass
        def load_oracle(self):pass
        def native_one(self,reader,h):
            if len(h)!=8:raise ValueError('bad synthetic/pilot grid')
            if failure=='generation' and getattr(self,'warm',False):raise ValueError('Injected generation failure')
            self.warm=True
            return [[dict(raw='fixture',text='fixture',malformed=False)]for _ in h]
    class Gate:
        INPUT_SHA256='fixture'
        load_inputs=staticmethod(lambda *a:None)
        run_gate=staticmethod(lambda *a:None)
    clock=W.Clock(tmp_path,time.time()+3600)
    def no_fit(*a):raise W.NoFit('Injected remaining forecast refusal')
    clock.forecast=no_fit
    go=tmp_path/'GO.json';go.write_text('{}')
    a=SimpleNamespace(out=tmp_path,inputs=tmp_path,assets=tmp_path/'assets',go=go,input_sha='input',source_sha='source')
    items=[dict(id=f'{i:024x}',vector_index=i)for i in range(8)]
    env=dict(vars(W),a=a,ass={'gpu_type':'H200'},reader='oracle',items=items,h=np.ones((8,5120),dtype=np.float32),clock=clock,status='FAILED',timer=SimpleNamespace(cancel=lambda:None),imports=lambda:(Backend,Gate))
    with pytest.raises((ValueError,W.NoFit)):
        exec(compile(ast.fix_missing_locations(ast.Module(body=[guard],type_ignores=[])),'<actual-reader-try-handlers>','exec'),env)
    sealed=json.loads((tmp_path/'OUTPUT_SEAL.json').read_text())
    assert sealed['status']==('FAILED'if failure=='generation'else'NO_FIT')
    assert (tmp_path/'FAILURE.json').exists()
    records=list((tmp_path/'records').glob('*.json'))
    assert len(records)==(0 if failure=='generation'else 8)
    assert (sealed['first_output_utc']=='unknown')==(failure=='generation')
    if records:assert sealed['first_output_evidence']['scope']=='first production greedy readout'


def test_new_recapture_publication_gate_and_deadline_fallback():
    go=valid_go()
    for key,value in [('block42_recapture_sha256','x'*64),('recapture_git_verified',False),('recapture_published_before_GO',False),('recapture_shared_commit','bad'),('recapture_sealed_epoch',2)]:
        with pytest.raises(ValueError):W.validate_go(dict(go,**{key:value}),'inputs','oracle',3)
    fallback=dict(go,oracle_only_deadline_fallback=True,issued_epoch=W.FALLBACK_EPOCH)
    W.validate_go(fallback,'inputs','oracle',W.FALLBACK_EPOCH+1)
    with pytest.raises(ValueError):W.validate_go(dict(fallback,issued_epoch=W.FALLBACK_EPOCH-1),'inputs','oracle',W.FALLBACK_EPOCH)
    with pytest.raises(ValueError):W.validate_go(dict(fallback,input_sha256_by_reader={'nla':'inputs'}),'inputs','nla',W.FALLBACK_EPOCH+1)


def test_exact_recapture_file_bound_and_no_failed_or44_capture(tmp_path):
    recap=dict(status='COMPLETE',sites=[42],capture_items=6720,operational_ruling='5ad0c3ce',bank_seal_sha256=W.BANK,
        original_capture_seal_sha256=W.CAPTURE,forecast_sha256=W.FORECAST,source_seal_sha256=W.RECAPTURE_SOURCE,
        public_items_sha256='22a5870f5ab41e520787b88c79dab3af463bfb36461edeea518bc2501488a6ef',
        original_block44_sha256='e1447c98cc534328dd98fdc19743a841de9849c8db3013477f26a3b627becce2',
        retained_oracle_test44_sha256='113acaaeb7b292d283dfe91ee12a480b7e5b29f74dab35666211ea8c91756bee',
        reader_outputs=0,completed_utc='1970-01-01T00:00:01+00:00',gpu_type='H200',files={'acts42.npy':'c'*64})
    path=tmp_path/'BLOCK42_RECAPTURE_SEAL.json'
    def bind(r):
        path.write_text(json.dumps(r));digest=W.sha(path)
        return dict(files={path.name:digest},block42_vector_source_sha256='c'*64),dict(valid_go(),block42_recapture_sha256=digest)
    inputs,go=bind(recap);W.verify_recapture_binding(tmp_path,inputs,go,'nla')
    for change in [dict(status='FAILED'),dict(sites=[42,44]),dict(source_seal_sha256='old'),dict(reader_outputs=1)]:
        inputs,go=bind(dict(recap,**change))
        with pytest.raises(ValueError):W.verify_recapture_binding(tmp_path,inputs,go,'oracle')
    inputs,go=bind(recap);inputs['block42_vector_source_sha256']='old42'
    with pytest.raises(ValueError):W.verify_recapture_binding(tmp_path,inputs,go,'nla')
    path.write_text('{}')
    with pytest.raises(ValueError):W.verify_recapture_binding(tmp_path,inputs,go,'oracle')


def test_first_output_includes_earlier_validation_analysis(tmp_path):
    import os
    (tmp_path/'parity').mkdir();(tmp_path/'records').mkdir()
    parity=tmp_path/'parity/PARITY_RESULT.json';parity.write_text('{}')
    record=tmp_path/'records/item.json';record.write_text('{}')
    os.utime(parity,ns=(1_000_000_000,1_000_000_000));os.utime(record,ns=(2_000_000_000,2_000_000_000))
    timestamp,evidence=W.first_output_info(tmp_path)
    assert timestamp=='1970-01-01T00:00:01+00:00'
    assert evidence['path']=='parity/PARITY_RESULT.json' and evidence['mtime_ns']==1_000_000_000
