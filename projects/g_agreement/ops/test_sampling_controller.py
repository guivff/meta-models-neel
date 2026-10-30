from pathlib import Path
import io,json,tarfile,hashlib
from types import SimpleNamespace
import pytest
from projects.g_agreement.ops import i5_sampling_controller as W

@pytest.mark.parametrize('case',['partial','corrupt','false_complete'])
def test_final_archive_retains_partial_but_rejects_corrupt_or_false_complete(tmp_path,monkeypatch,case):
    raw=json.dumps(dict(id='opaque',repeat=0)).encode();h=hashlib.sha256(raw).hexdigest()
    seal=dict(experiment='E103',source_seal_sha256='source',public_source_sha256='public',files={'jobs/opaque.0.json':h if case!='corrupt'else'0'*64},completed_samples=1,status='COMPLETE'if case=='false_complete'else'FAILED',gpu_type='H200')
    def fake(cmd,stdout,**kwargs):
        with tarfile.open(fileobj=stdout,mode='w:gz')as t:
            for name,data in [('out/jobs/opaque.0.json',raw),('out/OUTPUT_SEAL.json',json.dumps(seal).encode())]:
                m=tarfile.TarInfo(name);m.size=len(data);t.addfile(m,io.BytesIO(data))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(W.subprocess,'run',fake)
    state=dict(run=str(tmp_path),addr='127.0.0.1:22',gpu_type='H200');plan=dict(source_seal_sha256='source',public_sha256='public',item_ids=['opaque'])
    if case=='partial':
        assert W.archive(state,plan,True)['status']=='FAILED'
        assert(tmp_path/'final.pax.tar.gz').exists()
    else:
        with pytest.raises(ValueError):W.archive(state,plan,True)
        assert not(tmp_path/'final.pax.tar.gz').exists()

def test_retire_only_own_guards_and_escalate_if_term_is_deferred(tmp_path,monkeypatch):
    import signal
    stock=tmp_path/'stock_guards';stock.mkdir()
    (stock/'state').write_text('hardstop_pid=101\nhardstop_caffeinate_pid=102\nwatchdog_pid=103\nwatchdog_caffeinate_pid=104\n')
    killed=[]
    monkeypatch.setattr(W.subprocess,'check_output',lambda cmd,**k:str(stock)+'/ws2_hardstop.sh'if cmd[-1]=='101'else'other-process')
    monkeypatch.setattr(W.subprocess,'run',lambda *a,**k:SimpleNamespace(stdout=str(stock)+'/ws2_hardstop.sh'))
    monkeypatch.setattr(W.os,'kill',lambda pid,sig:killed.append((pid,sig)))
    monkeypatch.setattr(W.time,'sleep',lambda *a:None)
    W.retire_stock(tmp_path)
    assert killed==[(101,signal.SIGTERM),(101,signal.SIGKILL)]
