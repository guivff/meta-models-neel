import pytest
from projects.g_agreement.e95.judge_delivery import normalized,append_once


def test_normalization_copies_code_without_reparse_and_keeps_transport_missing():
    code=dict(id='a',category='silent',values=[],evidence='',first_position=None)
    rows=[dict(id='a',status='KEPT',code=code),dict(id='b',status='UNPARSEABLE',code=None,terminal_reason='UNKNOWN_REQUEST_NO_REPLAY')]
    out=normalized(rows)
    assert out[0]is code and out[1]==dict(id='b',category='UNPARSEABLE',values=[],evidence='',first_position=None)
    with pytest.raises(ValueError):normalized([dict(id='b',status='INVALID',code=None)])
    with pytest.raises(ValueError):normalized([dict(id='b',status='UNPARSEABLE',code=code)])


def test_handoff_is_idempotent_for_same_completed_stage(tmp_path):
    p=tmp_path/'HANDOFF.md';append_once(p,'E95-STAGE1-TERMINAL','sealed');original=p.read_bytes()
    append_once(p,'E95-STAGE1-TERMINAL','sealed')
    assert p.read_bytes()==original


def test_sealed_delivery_never_publishes_codes_evidence_labels_or_private_join(tmp_path,monkeypatch):
    from projects.g_agreement.e95 import judge_delivery
    monkeypatch.setattr(judge_delivery,'reuse_lineage',lambda:dict(judgment_seal_sha256='e'*64))
    from projects.g_agreement.e95.judge_delivery import deliver
    from projects.g_agreement.readerbench.io import write,read,sha
    job=tmp_path/'job';job.mkdir();packet=tmp_path/'packet';packet.mkdir()
    code=dict(id='a',category='states_value',values=['A'],evidence='SYNTHETIC_PRIVATE_QUOTE',first_position=0)
    rows=[dict(id='a',status='KEPT',code=code),dict(id='b',status='UNPARSEABLE',code=None)]
    write(job/'JUDGMENTS.json',rows);write(job/'ORIGINAL_JUDGMENTS.json',[rows[0]])
    cost=dict(booked_usd='.05',known_provider_cost_usd='.005',booked_429_upper_bound_usd='0',unknown_physical_reserve_usd='.045',lifetime_cap_usd='60',upper_bound_provenance=dict(events=['PRIVATE_EVENT']))
    write(job/'COUNTS.json',dict(cost=cost))
    write(job/'JUDGMENT_SEAL.json',dict(status='TERMINAL_BLIND_GRID_NO_ANALYSIS',judging_stage=1,route_verified=True,first_output_utc='synthetic',files={n:sha(job/n)for n in('JUDGMENTS.json','ORIGINAL_JUDGMENTS.json','COUNTS.json')}))
    write(packet/'GROUPED_PACKET.json',[dict(id='a'),dict(id='b')]);write(packet/'ORIGINAL_IDS.json',['a']);write(packet/'PRIVATE_JOIN.json',[dict(id='a',true_label=1,target='A',source_item_id='SYNTHETIC_PRIVATE_SOURCE'),dict(id='b',target=None)])
    write(packet/'PACKET_SEAL.json',dict(files={n:sha(packet/n)for n in('GROUPED_PACKET.json','ORIGINAL_IDS.json','PRIVATE_JOIN.json')}))
    spec=dict(judging_stage=1,out=str(job),packet=str(packet),packet_seal_sha256=sha(packet/'PACKET_SEAL.json'),stage_sources={})
    for field in('source_seal','regex_audit','stage_inventory','route','custody_receipt','budget_receipt'):spec[field]='private-source';spec[field+'_sha256']='f'*64
    sp=tmp_path/'SPEC.json';write(sp,spec);private=tmp_path/'delivery';pub=tmp_path/'public'
    receipt=deliver(sp,private,pub);raw=(pub/'RECEIPT.json').read_text()
    assert all(secret not in raw for secret in('SYNTHETIC_PRIVATE_QUOTE','SYNTHETIC_PRIVATE_SOURCE','true_label','PRIVATE_EVENT'))
    assert read(private/'JUDGMENTS.json')[1]['category']=='UNPARSEABLE'
    assert receipt['cumulative_E95_bank_cost']['unknown_physical_reserve_usd']=='.045'
    before=sha(private/'DELIVERY_SEAL.json');assert deliver(sp,private,pub)==receipt
    assert sha(private/'DELIVERY_SEAL.json')==before
