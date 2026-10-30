import ast,copy,random
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pytest
from . import gates,protocol,runner


def admission():
    return dict(experiment='E130',input_sha256='packet',runner_duties_delivered=gates.DUTIES,
                adapter_tests_passed=True,adapter_commit='a'*40,operator='Track Q',cap_seconds=1800,
                attempt_kind='planning',hard_stop_utc='2026-10-30T12:50:00Z')


def test_trigger_only_on_sealed_E127_analysis_by_cutoff():
    r=dict(experiment='E127',status='COMPLETE_ONCE',flipped_n=49,R_NAT1='DESCRIPTIVE ONLY',falsifier='DESCRIPTIVE ONLY')
    assert gates.e129_trigger(r,'2026-10-30T07:00:00Z')=='TRIGGERED'
    assert gates.e129_trigger(r,'2026-10-30T07:00:01Z')=='NOT_RUN_OPERATIONAL'
    for a,b,want in [('MET','NOT MET','NOT_RUN_NOT_NEEDED'),('NOT MET','MET','NOT_RUN_NOT_NEEDED'),('NOT MET','NOT MET','TRIGGERED')]:
        r.update(flipped_n=50,R_NAT1=a,falsifier=b)
        assert gates.e129_trigger(r,'2026-10-29T18:00:00Z')==want
    r['status']='PENDING'
    with pytest.raises(ValueError):gates.e129_trigger(r,'2026-10-29T18:00:00Z')


def test_e130_requires_delivered_duties_packet_deadline_and_adapter():
    now=datetime(2026,10,29,18,tzinfo=timezone.utc)
    assert gates.e130_admit(admission(),'packet','2026-10-30T07:00:00Z',now)
    for key,value in [('runner_duties_delivered',{}),('adapter_tests_passed',False),('adapter_commit','x'*40),('cap_seconds',1801)]:
        r=admission();r[key]=value
        with pytest.raises(ValueError):gates.e130_admit(r,'packet','2026-10-29T18:00:00Z',now)
    with pytest.raises(ValueError):gates.e130_admit(admission(),'packet','2026-10-30T07:00:01Z',now)
    with pytest.raises(ValueError):gates.e130_admit(admission(),'packet','2026-10-29T18:00:00Z',gates.CREATE.replace(hour=11))


def test_single_measured_attempt_requires_original_evidence():
    r=admission();r.update(attempt_kind='measured',prior_no_fit_seal='a'*64,measured_need_seconds=1600,cap_seconds=2060)
    assert gates.e130_admit(r,'packet','2026-10-29T18:00:00Z',datetime(2026,10,29,18,tzinfo=timezone.utc))
    r['cap_seconds']=2061
    with pytest.raises(ValueError):gates.e130_admit(r,'packet','2026-10-29T18:00:00Z',datetime(2026,10,29,18,tzinfo=timezone.utc))


def test_exp24_shuffle_and_cap_empty_without_input_mutation():
    def encode(text):return list(range(300)) if text=='long'else [77]
    dev=[dict(id='dev',ids=list(range(32)))];test=[dict(id='test',text='long'),dict(id='empty',text='')]
    before=copy.deepcopy((dev,test));rows=protocol.token_rows(dev,test,encode)
    assert (dev,test)==before and rows==protocol.token_rows(dev,test,encode)
    assert rows[0]['ids']==list(range(32)) and rows[1]['ids']==list(range(256))
    assert sorted(rows[2]['ids'])==list(range(256)) and rows[1]['ids']!=rows[2]['ids']
    assert rows[3]['ids']==[77] and rows[4]['ids']==[77]


class FakeAR:
    class Tok:
        def encode(self,text,**kw):return [1,2,3]
    tok=Tok()
    def __init__(self):self.calls=[]
    def reconstruct(self,rows,layer,variant,batch):
        self.calls.append((copy.deepcopy(rows),layer,variant,batch))
        return np.full((len(rows),5120),len(self.calls),np.float32)


def test_rebuilds_are_native_no_whitener_or_raw_reference(tmp_path):
    ar=FakeAR();out=tmp_path/'out'
    status=runner.acquire(ar,[dict(id='dev',ids=list(range(32)))],[dict(id='test',text='text')],out,lambda *a:True,gpu_type='synthetic CPU')
    assert status=='COMPLETE' and len(ar.calls)==3
    assert all(x[1:]==(44,('li','ln'),16)for x in ar.calls)
    assert np.array_equal(np.load(out/'rebuild-0000.npy'),np.full((1,5120),1,np.float32))
    with pytest.raises(FileExistsError):runner.acquire(ar,[],[],out,lambda *a:True,gpu_type='synthetic CPU')


def test_no_fit_before_first_batch_does_not_call_reconstructor(tmp_path):
    ar=FakeAR()
    assert runner.acquire(ar,[dict(id='dev',ids=list(range(32)))],[],tmp_path/'out',lambda *a:False,gpu_type='synthetic CPU')=='NO_FIT'
    assert ar.calls==[]


def test_local_assets_refuse_remote_or_wrong_revision_before_model(tmp_path):
    with pytest.raises(ValueError):runner.resolve_snapshot(tmp_path,'pinned')


def test_ported_reference_arithmetic_unchanged_without_executing_reference():
    # Read the immutable reference as text only, never import or execute its checkout.
    import hashlib
    ref=Path(__file__).resolve().parents[3]/'cache/g_agreement/understand/e125/wlens_adapter234/reference'
    if not ref.exists():pytest.skip('reference is local verification evidence, not a runtime dependency')
    original=(ref/'lib24.py').read_bytes()
    assert hashlib.sha256(original).hexdigest()=='c5f1b4215d5a18046d2a1467b7bab9fe57e1407678189fdb404d2e29ae9fd76d'
    def funcs(text):return {n.name:n for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    old=funcs(original);new=funcs(Path(protocol.__file__).read_text())
    for name in ('shuffle_tokens','_readout_ids'):
        assert [ast.dump(n)for n in old[name].body]==[ast.dump(n)for n in new[name].body]
    old=funcs((ref/'olens_ar.py').read_text())['OLensAR']
    new=funcs((Path(__file__).parent/'olens_ar.py').read_text())['OLensAR']
    old={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)};new={n.name:n for n in new.body if isinstance(n,ast.FunctionDef)}
    assert ast.dump(old['reconstruct'])==ast.dump(new['reconstruct'])
    assert ast.dump(old['_head_norm'])==ast.dump(new['_head_norm'])
