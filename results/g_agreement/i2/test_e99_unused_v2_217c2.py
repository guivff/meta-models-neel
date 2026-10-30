import importlib.util,sys,json,types,ast,re
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'cache/g_agreement/i2/publication'));sys.path.insert(0,str(Path(__file__).parent));sp=importlib.util.spec_from_file_location('v2',Path(__file__).with_name('e99_continue_unused_v2_217c2.py'));M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)
def setup(tmp_path,monkeypatch):
 monkeypatch.setattr(M,'H',tmp_path);monkeypatch.setattr(M.time,'sleep',lambda x:None);return []
def test_transient_global_read_retry_sends_nothing(tmp_path,monkeypatch):
 calls=setup(tmp_path,monkeypatch)
 def run(args,**kw):
  calls.append(args)
  if len(calls)==1:return types.SimpleNamespace(returncode=1,stderr=b'transient CPU read')
  p=ast.literal_eval(re.search(r'Path\((.+)\)\.write_text',args[2]).group(1));Path(p).write_text(json.dumps(dict(actual_plus_open_caps_usd='100',unknown_physical_holds_usd='0')));return types.SimpleNamespace(returncode=0,stderr=b'')
 monkeypatch.setattr(M.subprocess,'run',run);p,d=M.snapshot();assert len(calls)==2 and d['actual_plus_open_caps_usd']=='100';assert len(list((tmp_path/'global_audits').glob('*.failure0.json')))==1
 assert all('snapshot' in x[2]for x in calls)
def test_persistent_global_failure_stops_after_three_reads(tmp_path,monkeypatch):
 calls=setup(tmp_path,monkeypatch)
 def run(args,**kw):calls.append(args);return types.SimpleNamespace(returncode=1,stderr=b'CPU read failed')
 monkeypatch.setattr(M.subprocess,'run',run)
 with pytest.raises(AssertionError,match='FRESH_GLOBAL_SNAPSHOT_FAILED'):M.snapshot()
 assert len(calls)==3 and len(list((tmp_path/'global_audits').glob('*.failure*.json')))==3
