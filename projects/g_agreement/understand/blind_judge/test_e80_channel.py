from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from projects.g_agreement.understand.blind_judge import e80_channel as m

SOURCE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/results/g_agreement/understand/e80')

def fixture():
    export=json.loads((SOURCE/'EXPORT_SEAL.json').read_text())
    seal=dict(wtext_source=str(SOURCE),renderer_files={n:export['files'][n] for n in ('export80.py','regex80.py','render_judge80.py')})
    renderer,regex=m.load_renderers(seal)
    packets=json.loads((SOURCE/'cache/export_2026-10-28_v3/JUDGES.PRIVATE.json').read_text())
    return renderer,regex,packets


def test_every_frozen_prompt_and_route():
    renderer,regex,packets=fixture();protocol=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global')
    n=0
    for packet in packets:
        sample='Synthetic readout.\n- a result'
        if packet['headline_scorer']=='regex':
            with pytest.raises(ValueError):m.wire_for(packet,sample,protocol,renderer)
            continue
        w=m.wire_for(packet,sample,protocol,renderer);call=renderer.judge_messages(packet,sample)[0]
        assert w['messages']==[dict(role='system',content=call['system']),dict(role='user',content=call['user'])]
        assert w['response_format']['json_schema']==packet['schema']
        assert w['provider']['only']==['google-vertex/global'] and w['provider']['zdr'] is True
        assert w['provider']['data_collection']=='deny' and w['provider']['allow_fallbacks'] is False
        n+=1
    assert n==420


def test_schema_and_wrong_model():
    renderer,_,packets=fixture();p=next(p for p in packets if p['mode']=='basic')
    assert m.valid_response(dict(expressed=False,target='',quote=''),p)['expressed'] is False
    for v in ({'expressed':'false','target':'','quote':''},{'expressed':False,'target':'','quote':'','extra':0}):
        with pytest.raises(ValueError):m.valid_response(v,p)
    with pytest.raises(ValueError):m.wire_for(p,'synthetic',SimpleNamespace(MODEL='google/gemini-3.8-flash',PROVIDER='google-vertex/global'),renderer)
    p=next(p for p in packets if p['mode']=='chain')
    m.valid_response(dict(states_value=True,values=[14],basis='arithmetic',quote='14'),p)
    with pytest.raises(ValueError):m.valid_response(dict(states_value=True,values=[True],basis='arithmetic',quote='14'),p)
