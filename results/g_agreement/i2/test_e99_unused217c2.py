import importlib.util,json,sys,types
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(R/'cache/g_agreement/i2/publication'))
spec=importlib.util.spec_from_file_location('transport221',Path(__file__).with_name('e99_transport217c2_resume.py'));M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
def receipt(**kw):
 d=dict(issuer='integrator',verified=True,E99_allocation_usd=150,phase1_calls=6680,continuation_requires_actual_gate=True,reservation_included=True,global_judging_committed_including_reservation_usd=220);d.update(kw);return d
@pytest.mark.parametrize('change',[dict(E99_allocation_usd=40),dict(E99_allocation_usd=400),dict(phase1_calls=100),dict(continuation_requires_actual_gate=False),dict(global_judging_committed_including_reservation_usd=1001)])
def test_no_old_or_unconditional_cap(change):
 with pytest.raises(ValueError):M.E99ContinuationTransport({},'opaque',receipt(**change))
def harness(tmp_path,monkeypatch,bodies):
 t=M.E99ContinuationTransport.__new__(M.E99ContinuationTransport);t.root=tmp_path;t.protocol=types.SimpleNamespace();t.io=types.SimpleNamespace();t.privacy=types.SimpleNamespace();t.saved=(None,None,lambda *a:None,None);t.before_send=lambda w:None;t.paused=[];t.pause_all=lambda p:t.paused.append(p)
 monkeypatch.setattr(M,'frozen_wire',lambda *a:{'opaque':'wire'});monkeypatch.setattr(M,'validate_wire_privacy',lambda *a:None)
 t.calls=[]
 def one(stage,items):
  i=len(t.calls);t.calls.append((stage,items));p=tmp_path/stage;p.mkdir(exist_ok=True);(p/'r.response.json').write_text(json.dumps(bodies[min(i,len(bodies)-1)]));return dict(id='r',status='OK',value={})
 t.client=types.SimpleNamespace(one=one);return t

def body(finish='stop',content='{}',**changes):
 b=dict(http_status=200,response=dict(provider='Google',model='google/gemini-3.1-flash-lite',usage=dict(cost=0.001),choices=[dict(finish_reason=finish,message=dict(content=content))]));b['response'].update(changes);return b

def test_length_never_retried(tmp_path,monkeypatch):
 t=harness(tmp_path,monkeypatch,[body('length')]);r=t.call('a'*32,{});assert len(t.calls)==1 and r['reason']=='CHARGED_LENGTH_TERMINAL_NO_RETRY'
def test_402_pauses_all(tmp_path,monkeypatch):
 t=harness(tmp_path,monkeypatch,[dict(http_status=402,response={})]);
 with pytest.raises(RuntimeError,match='HTTP402'):t.call('a'*32,{})
 assert len(t.paused)==len(t.calls)==1
@pytest.mark.parametrize('response',[body(error={'code':429}),body(provider='Other'),body('error'),dict(http_status=500,response={})])
def test_provider_errors_stop_without_retry(tmp_path,monkeypatch,response):
 t=harness(tmp_path,monkeypatch,[response])
 with pytest.raises((ValueError,RuntimeError)):t.call('a'*32,{})
 assert len(t.calls)==1

def test_schema_failures_only_max_two_retries(tmp_path,monkeypatch):
 t=harness(tmp_path,monkeypatch,[body()]);monkeypatch.setattr(M,'terminal_record',lambda *a:dict(id='a'*32,status='UNPARSEABLE',reason='SCHEMA'))
 r=t.call('a'*32,{});assert len(t.calls)==3 and len(r['attempt_history'])==3

def test_missing_callbacks_prevent_send(tmp_path,monkeypatch):
 t=harness(tmp_path,monkeypatch,[body()]);t.before_send=None
 with pytest.raises(ValueError):t.call('a'*32,{})
 assert not t.calls

def test_explicit_zero_error_terminal_never_retried(tmp_path,monkeypatch):
 b=body('error');b['response']['usage']['cost']=0;t=harness(tmp_path,monkeypatch,[b]);r=t.call('a'*32,{})
 assert r['status']=='FAILED' and r['reason']=='INCOMPLETE_COMPLETION' and len(t.calls)==1

def test_unused_roster_preserves_failed_and_prior():
 spec=importlib.util.spec_from_file_location('continuation',Path(__file__).with_name('e99_continue_unused217c2.py'));d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
 calls=[dict(id=f'{i:032x}')for i in range(6680)];prior=calls[:106];xs=d.unused_roster(calls,prior,calls[106]['id']);assert xs==calls[107:] and len(xs)==6573
 with pytest.raises(AssertionError):d.unused_roster(calls,prior,prior[0]['id'])
