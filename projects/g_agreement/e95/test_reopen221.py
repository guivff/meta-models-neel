from pathlib import Path
from projects.g_agreement.e95 import reopen220,reopen221
from projects.g_agreement.e95.test_reopen220 import inputs


def test_strict_positive_cannot_reopen_corrected_gate(tmp_path,monkeypatch):
    a,d=inputs(tmp_path/'strict',count=2)
    names=[str(x.relative_to(tmp_path)) for x in (a,d)]
    monkeypatch.setattr(reopen220.subprocess,'check_output',lambda *a,**k:'\n'.join(names))
    assert reopen221.check(tmp_path)['status']=='WAITING_CORRECTED_E87_ANALYSIS_SEAL'


def test_only_corrected_labels_decide_once(tmp_path,monkeypatch):
    a,d=inputs(tmp_path/'strict',count=2)
    ca,cd=inputs(tmp_path/'E87_validator_corrected221',count=0)
    names=[str(x.relative_to(tmp_path)) for x in (a,d,ca,cd)]
    monkeypatch.setattr(reopen220.subprocess,'check_output',lambda *a,**k:'\n'.join(names))
    result=reopen221.check(tmp_path)
    assert result['status']=='KEEP_NOT_RUN' and result['consumed_or_late_missed_rows']==0
    assert 'corrected' in result['analysis_seal_path']
