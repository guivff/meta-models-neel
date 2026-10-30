import json,shutil
from pathlib import Path
import numpy as np
import pytest
from projects.g_agreement.e136.dev2 import runner as r
from projects.g_agreement.e136.test_runner import item
from projects.g_agreement.e127.test_runner import Tiny
from types import SimpleNamespace

def test_original_code_objects_and_observer_single_pass():
    assert r.capture_batch.__code__ is r.original.capture_batch.__code__
    assert r.oracle_batch.__code__ is r.original.oracle_batch.__code__
    assert r._natural.__code__ is r.original.runner109.natural_capture.__code__
    m=Tiny();out=r.capture_batch(m,[item()])
    assert m.calls==1 and set(out['captures'])=={44} and out['generation_calls']==0 and not out['intervention_installed']
    assert np.array_equal(out['captures'][44],m.snapshots[0][44][:,11].numpy())
    assert not m._forward_hooks and all(not b._forward_hooks for b in m.layers)

def test_only44_native_and_unchanged_sweep():
    class Oracle:
        def verbalize(self,vectors,layer,k,sampling,batch):
            assert layer==44 and k==1 and batch==8 and sampling.max_new_tokens==128 and sampling.temperature==0
            return [['fixture']]
    rt=SimpleNamespace(readers=SimpleNamespace(oracle=Oracle()),sweep_batch_size=8)
    v=np.ones((1,5120),np.float32);before=v.copy()
    assert r.oracle_batch(rt,v,44)[0]['text']=='fixture'and np.array_equal(v,before)
    for L in (36,52,60):
        with pytest.raises(ValueError):r.oracle_batch(rt,v,L)

def test_exception_cleanup():
    m=Tiny();m.fail_call=1
    with pytest.raises(RuntimeError):r.capture_batch(m,[item()])
    assert not m._forward_hooks and all(not b._forward_hooks for b in m.layers)

def test_exact_actual_subset_and_no_reauthoring():
    base=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e136-dev2-inputs-v1/inputs')
    xs,_=r.load(base,r.BANK_SHA)
    old=json.loads(Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e136-bank-v2/inputs/items.json').read_text())
    chosen={x['id']for x in xs}
    assert xs==[x for x in old if x['id']in chosen]and len(xs)==400
    assert len(list(r.batches(xs)))==61 and sum(map(len,r.batches(xs)))==400
    with pytest.raises(ValueError):r.load(base,r.original.BANK_SHA)

def test_public_labels_and_modified_members_refused(tmp_path):
    x=item();x['cue']='private'
    with pytest.raises(ValueError):r.validate_items([x])
    base=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e136-dev2-inputs-v1/inputs');shutil.copytree(base,tmp_path/'inputs')
    f=tmp_path/'inputs/items.json';f.write_text(f.read_text()+' ')
    with pytest.raises(ValueError):r.load(tmp_path/'inputs',r.BANK_SHA)
