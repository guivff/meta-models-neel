"""No new runner logic: verify config scope and reused native primitives."""
import json
from pathlib import Path
from projects.g_agreement.e100.contract import sha,verify
from projects.g_agreement.e120 import test_configs as native_tests
HERE=Path(__file__).parent

def config():return json.loads((HERE/'timing.json').read_text())

def test_frozen376_scope_layers_greedy_privacy_and_parallel_release():
    c=config();assert c['experiment']=='E116' and c['items']==376 and c['readouts']==752
    assert c['expected_arm_counts']=={'immediate':329,'delayed':47}
    assert c['source_capture_layers']==c['oracle_read_layers']==[52,60]
    assert c['capture']['patches'] is False and c['reader']['temperature']==0 and c['reader']['max_new_tokens']==128 and c['reader']['k']==1
    assert c['public_fields']==['id','ids','read_index'] and c['labels_on_pod'] is False and c['cpu_only_labels']['stage_to_pod'] is False
    assert 'parallel launch' in c['launch']['mode'] and c['judging']['bank']=='E116'

def test_original_public_packet_census_last_token_and_no_choice_labels():
    c=config();p=c['public_input'];root=Path(p['root']);verify(root,'INPUT_SEAL.json',p['input_sha256'])
    xs=json.loads((root/'items.json').read_text());assert len(xs)==376 and len({x['id'] for x in xs})==376
    assert all(set(x)=={'id','ids','read_index'} and x['read_index']==len(x['ids'])-1 for x in xs)
    assert sha(p['archive'])==p['archive_sha256']

def test_e116_reuses_actual_configured_natural_capture_and_greedy_sweep(monkeypatch):
    c=config();monkeypatch.setattr(native_tests,'configs',lambda:(c,None))
    native_tests.test_configured_natural_read_site_capture_52_60(monkeypatch)
    native_tests.test_original_greedy_sweep_keeps_actual_layer_and_one_readout()
