import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from projects.g_agreement.e108_ops.watch_analysis import run


def setup(tmp_path):
    count=[]
    a=SimpleNamespace(GUARD=tmp_path/'guard',committed=lambda:count.append('source'),inputs=lambda s:count.append('inputs'),core=SimpleNamespace(verify=lambda *x:count.append('verify')))
    seal=tmp_path/'OUTPUT_SEAL.json';seal.write_text(json.dumps(dict(status='COMPLETE')))
    spec=tmp_path/'SPEC.json';spec.write_text(json.dumps(dict(output_seal=str(seal),output_sha256=hashlib.sha256(seal.read_bytes()).hexdigest(),analysis=str(tmp_path/'analysis'))))
    return a,count,spec,seal


def test_partial_bank_never_claims(tmp_path):
    a,c,s,seal=setup(tmp_path);assert run(tmp_path/'missing',a)[0]=='WAITING_SPEC'
    seal.unlink();assert run(s,a,True,lambda:c.append('RUN'))[0]=='WAITING_COMPLETE_BANK';assert c==[]


def test_default_is_check_only(tmp_path):
    a,c,s,seal=setup(tmp_path);assert run(s,a)[0]=='READY';assert c==['source','inputs']


def test_complete_execution_is_not_replayed(tmp_path):
    a,c,s,seal=setup(tmp_path)
    def runner():
        c.append('RUN');(tmp_path/'analysis').mkdir();(tmp_path/'analysis/ANALYSIS_SEAL.json').write_text('{}');a.GUARD.touch()
    assert run(s,a,True,runner)[0]=='COMPLETE_ONCE'
    assert run(s,a,True,runner)[0]=='ALREADY_COMPLETE';assert c.count('RUN')==1


def test_consumed_incomplete_guard_stops(tmp_path):
    a,c,s,seal=setup(tmp_path);a.GUARD.touch()
    with pytest.raises(AssertionError,match='never replay'):run(s,a,True,lambda:c.append('RUN'))
    assert 'RUN' not in c


def test_wrong_source_hash_stops(tmp_path):
    a,c,s,seal=setup(tmp_path);seal.write_text('{"status":"COMPLETE","changed":true}')
    with pytest.raises(AssertionError,match='hash'):run(s,a,True)
