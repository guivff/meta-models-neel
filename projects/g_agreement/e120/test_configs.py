"""Configuration tests exercise the unchanged E109/E87 and E113 callables."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
from projects.g_agreement.e101.runner import dependencies
dependencies()
from projects.g_agreement.e101 import runner109
from projects.g_agreement.e113.capture import capture_lens
from projects.g_agreement.e113.test_capture import Tiny,Layer,lens
HERE=Path(__file__).parent

def configs():return [json.loads((HERE/n).read_text()) for n in ('timing.json','decoder.json')]

def test_frozen_population_sites_privacy_and_launch_order():
    a,b=configs();assert a['items']==400 and a['readouts']==800 and a['source_capture_layers']==a['oracle_read_layers']==[52,60]
    assert b['items']==600 and b['splits']=={'dev':200,'test':400} and b['source_block']==44
    assert b['capture']['lens_layers']==list(range(64)) and b['capture']['positions']==['injected_activation','first_generated_token']
    for c in (a,b):
        assert c['labels_on_pod'] is False and c['cpu_only_labels']['stage_to_pod'] is False and 'parallel launch' in c['launch']['mode']
        assert not {'genre','addressed','label','target'} & set(c['public_fields'])
        assert c['native_alpha']==16000 and c['native_transform']=='unit'

def test_configured_natural_read_site_capture_52_60(monkeypatch):
    a,_=configs();monkeypatch.setattr(runner109,'CAPTURE',tuple(a['capture']['module_parameters']['CAPTURE']))
    class Natural(Tiny):
        def forward(self,input_ids,**kw):return super().forward(self.emb(input_ids),kw['attention_mask'],use_cache=False,logits_to_keep=1)
    m=Natural();m.layers=torch.nn.ModuleList([Layer() for _ in range(64)]);m.config.num_hidden_layers=64
    xs=[dict(ids=[1,2,3],read_index=2),dict(ids=[2,3,4],read_index=2)]
    h=runner109.natural_capture(m,xs)
    assert set(h)=={52,60} and all(x.shape==(2,4) for x in h.values())
    for layer,v in h.items():assert np.array_equal(v,m.history[0][layer][:,2].numpy())
    assert all(not x._forward_hooks for x in m.layers)

def test_original_greedy_sweep_keeps_actual_layer_and_one_readout():
    cls=runner109.backend87();b=cls(Path('/NOT_READ/assets.json'));calls=[]
    class Oracle:
        def verbalize(self,h,layer,k,sampling,batch):
            calls.append((layer,k,sampling.temperature,sampling.max_new_tokens,batch,h.clone()));return [['native synthetic'] for _ in h]
    b.readers=SimpleNamespace(oracle=Oracle());h=np.ones((2,4),np.float32)
    for layer in configs()[0]['oracle_read_layers']:
        result=b.sweep('oracle',h,layer);assert len(result)==2 and all(x['native_max_new_tokens']==128 for x in result)
    assert [x[:5] for x in calls]==[(52,1,0,128,8),(60,1,0,128,8)] and np.all(h==1)

def test_original_lens_capture_all64_both_actual_positions():
    m=Tiny();m.layers=torch.nn.ModuleList([Layer() for _ in range(64)]);m.config.num_hidden_layers=64
    states,tokens,meta=capture_lens(lens(m),np.ones((2,4),np.float32),layer=44)
    assert states.shape==(2,64,2,4) and tokens.shape==(2,1)
    assert meta['injected_position']==1 and meta['first_generated_position']==3
    for layer in range(64):
        assert np.array_equal(states[:,layer,0],m.history[0][layer][:,1].numpy())
        assert np.array_equal(states[:,layer,1],m.history[1][layer][:,3].numpy())
    assert all(not x._forward_hooks for x in m.layers)
