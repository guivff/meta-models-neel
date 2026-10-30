import hashlib
from copy import deepcopy
import pytest
from .e117_sensitivity_binding import project


def fixture():
    h=lambda s:hashlib.sha256(s.encode()).hexdigest()
    joins=[dict(id='a',part='main',item_id='e113',descriptor_ref_id='e113',row='fact_recall',source_bank='E56',alpha=2,arm='T',native_id='nativeA',source_ref=dict(member='jobs/a.json',keys=[2,'text']))]
    units=[dict(id='a',data=dict(readout='copy'))];original={'a':'source'}
    descriptors={'e113':dict(source_id='e113',row='fact_recall',source_bank='E56',original_source_id='E56-original',original_packet_indices=[5],original_key_indices=[8])}
    audit=dict(bank='E117',n_records=1,redacted_records=1,affected=[dict(id='a',original_readout_sha256=h('source'),judge_readout_sha256=h('copy'),path_count=1,address_count=0)])
    return joins,audit,units,original,descriptors


def test_exact_source_ids_hashes_and_audit_are_copied_without_scores():
    args=fixture();out=project(*args,n=1,affected_n=1)
    assert out[0]['judgment_id']=='a' and out[0]['original_e113_item_id']=='e113' and out[0]['original_bank_item_id']=='E56-original'
    assert out[0]['original_audit']==args[1]['affected'][0] and out[0]['native_text_ref']['keys']==[2,'text']
    assert 'score' not in out[0] and 'label' not in out[0]


@pytest.mark.parametrize('fault',['foreign_id','source_hash','copy_hash','wrong_row','duplicate'])
def test_source_identity_or_hash_mismatch_fails_closed(fault):
    a=deepcopy(fixture())
    if fault=='foreign_id':a[1]['affected'][0]['id']='other'
    elif fault=='source_hash':a[3]['a']='changed'
    elif fault=='copy_hash':a[2][0]['data']['readout']='changed'
    elif fault=='wrong_row':a[0][0]['row']='other'
    else:a[0].append(deepcopy(a[0][0]))
    with pytest.raises((ValueError,KeyError)):project(*a,n=1,affected_n=1)
