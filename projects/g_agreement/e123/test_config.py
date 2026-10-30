"""E123 config binds existing native sweep to exact sealed unhooked vectors."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
from projects.g_agreement.e100.contract import sha,verify
from projects.g_agreement.e101.runner import dependencies
dependencies()
from projects.g_agreement.e101 import runner109
HERE=Path(__file__).parent

def config():return json.loads((HERE/'unhooked.json').read_text())

def test_frozen_scope_no_recapture_no_hook_greedy_privacy():
    c=config()
    assert c['items']==134 and c['readouts']==268 and c['expected_row_counts']=={'fact_recall':84,'language_plan':50}
    assert c['condition']=='unhooked' and c['source_capture_layers']==c['oracle_read_layers']==[44,52]
    assert c['capture']['enabled'] is False and c['capture']['patches'] is False
    assert c['labels_on_pod'] is False and c['cpu_only_labels']['stage_to_pod'] is False
    assert c['public_fields']==['id','vector_index']
    assert (c['native_alpha'],c['native_transform'])==(16000,'unit')
    assert (c['reader']['k'],c['reader']['temperature'],c['reader']['max_new_tokens'])==(1,0,128)
    assert c['launch']['owner']=='I-2' and c['launch']['planning_GPU_hours']==.4
    assert c['judging']['bank']=='E123' and c['judging']['max_USD']==3

def test_actual_original_sweep_forwards_exact_vectors_at44_and52():
    cls=runner109.backend87();b=cls(Path('/UNUSED/assets.json'));calls=[]
    class Oracle:
        def verbalize(self,h,layer,k,sampling,batch):
            calls.append((layer,k,sampling.temperature,sampling.max_new_tokens,batch,h.clone()))
            return [['synthetic native']for _ in h]
    b.readers=SimpleNamespace(oracle=Oracle())
    h=np.arange(12,dtype=np.float32).reshape(3,4);before=h.tobytes()
    for layer in config()['oracle_read_layers']:
        out=b.sweep('oracle',h,layer)
        assert len(out)==3 and all(x['native_max_new_tokens']==128 for x in out)
    assert [c[:5]for c in calls]==[(44,1,0,128,8),(52,1,0,128,8)]
    assert all(torch.equal(c[-1],torch.from_numpy(h))for c in calls) and h.tobytes()==before

def test_sealed_public_packet_exact_original_bytes_and_cpu_cohort():
    c=config();p=c['public_input'];root=Path(p['root']);verify(root,'INPUT_SEAL.json',p['input_sha256'])
    assert sha(p['archive'])==p['archive_sha256']
    xs=json.loads((root/'items.json').read_text());assert len(xs)==134
    assert all(set(x)=={'id','vector_index'}and x['vector_index']==i for i,x in enumerate(xs))
    assert len({x['id']for x in xs})==134
    private=c['cpu_only_labels'];assert sha(private['path'])==private['sha256']
    pointers=json.loads(Path(private['path']).read_text());source=c['source_output'];src=Path(source['seal']).parent
    assert sha(source['seal'])==source['sha256'];seal=json.loads(Path(source['seal']).read_text())
    order=json.loads((src/'ARRAY_ORDER.json').read_text());assert sha(src/'ARRAY_ORDER.json')==source['order_sha256']
    assert all(x['condition']=='unhooked'and x['split']=='test'and x['base_id']==order[x['row']]['test'][x['original_vector_index']]for x in pointers)
    for layer in (44,52):
        a=np.load(root/f'H{layer}.npy',allow_pickle=False);assert a.shape==(134,5120)and a.dtype==np.float32 and np.isfinite(a).all()
        originals={}
        for row in c['expected_row_counts']:
            member=f'arrays/{row}_test_unhooked_{layer}.npy';assert sha(src/member)==seal['files'][member]
            originals[row]=np.load(src/member,allow_pickle=False)
        assert all(a[i].tobytes()==originals[x['row']][x['original_vector_index']].tobytes()for i,x in enumerate(pointers))
