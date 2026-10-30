import pytest
from projects.g_agreement.e95.judge_parallel_ba2 import decision,INTERVAL

def fixture():return dict(interval_seconds=1,next_send_epoch=0,cooldown_until_epoch=0,waiting=[])

def test_never_takes_stage1_deadline_or_queued_priority_slot():
    s=fixture();own={}
    assert not decision(2,10,s,own,dict(next_send_epoch=11),None)
    assert not decision(2,10,s,own,dict(next_send_epoch=14.99),None)
    assert decision(2,10,s,own,dict(next_send_epoch=13),None)
    s['waiting']=[dict(bank='E140')]
    assert not decision(2,10,s,own,None,None)

def test_stage3_yields_stage2_and_pressure_in_order():
    s=fixture();second=dict(next_send_epoch=10,waiting_until_epoch=12)
    assert not decision(3,10,s,{},None,second)
    assert decision(2,10,s,{},None,None)
    assert not decision(3,10,s,{},None,None,pressure=True)
    assert not decision(2,10,s,{},None,None,priority_open=True)

def test_respects_existing_cooldown_and_lower_rate_caps():
    s=fixture();s['cooldown_until_epoch']=11
    assert not decision(2,10,s,{},None,None)
    s['cooldown_until_epoch']=0
    assert not decision(3,10,s,dict(next_send_epoch=11),None,None)
    assert 12+sum(60/x for x in INTERVAL.values())==24

def test_original_once_guard_cannot_be_claimed_twice(tmp_path,monkeypatch):
    from projects.g_agreement.e95 import judge_parallel_ba2 as b
    monkeypatch.setattr(b,'LEDGER',tmp_path)
    monkeypatch.setattr(b,'SOURCE',tmp_path/'source');(tmp_path/'source').write_text('{}')
    b.claim(tmp_path,2,'a'*64,tmp_path/'out')
    with pytest.raises(FileExistsError):b.claim(tmp_path,2,'a'*64,tmp_path/'out')

def test_seal_after_cutoff_is_not_complete(tmp_path,monkeypatch):
    import os
    from projects.g_agreement.readerbench.io import write,sha
    from projects.g_agreement.e95.judge_parallel_ba2 import timely
    member=tmp_path/'member';member.write_text('x')
    seal=tmp_path/'seal';write(seal,dict(files={'member':sha(member)}))
    marker=tmp_path/'marker';write(marker,dict(seal=str(seal),sha256=sha(seal)))
    os.utime(seal,(20,20));os.utime(marker,(20,20))
    assert timely(marker,21)
    assert not timely(marker,20)
