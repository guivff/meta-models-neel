import json,shutil
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.e138 import runner as r
from projects.g_agreement.e100 import interventions
from projects.g_agreement.e136.dev2 import runner as native
from results.g_agreement.understand.e76 import common76
from results.g_agreement.understand.e100.vectors import math100
ROOT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e138-inputs-v1/inputs')

def test_literal_original_protocols_and_native_code():
    assert r.transform is interventions.transform and r.norm_match is common76.norm_match
    assert r.pair_other is math100.pair_other and r.oracle_batch is native.oracle_batch

def test_e100_copy_not_normalized():
    h=np.ones((3,5120),np.float32);donor=np.full_like(h,3)
    before=donor.copy();out=r.transform(h,donor,'transplant')
    assert np.array_equal(out,donor)and np.array_equal(donor,before)and np.all(out==3)

def test_original_seed_gaussian_prefix_and_bankmedian_norm():
    full=np.random.default_rng(20261027).standard_normal((500,5120)).astype(np.float32)
    z=np.random.default_rng(20261027).standard_normal((84,5120)).astype(np.float32)
    assert np.array_equal(z,full[:84])
    h=np.zeros((3,5120),np.float32);h[:,0]=[2,4,9]
    target=np.full(3,np.median(np.linalg.norm(h.astype(np.float64),axis=1)))
    out=r.norm_match(z[:3],target)
    assert np.allclose(np.linalg.norm(out.astype(np.float64),axis=1),4,rtol=1e-6)
    assert np.array_equal(z,full[:84])

def test_original_pairing_seed_and_oppositeclass():
    labels=[0,1,0,1,0,1];ids=list('abcdef')
    donors=r.pair_other(ids,labels)
    assert donors==r.pair_other(ids,labels,20261028)
    assert all(labels[i]!=labels[j]and i!=j for i,j in enumerate(donors))

def test_native_one_greedy_and_vectors_unchanged():
    from projects.g_agreement.e100.worker import original
    original() # actual E79/runtime import sets the existing mats source path
    class Oracle:
        def verbalize(self,vectors,layer,k,sampling,batch):
            assert layer==44 and k==1 and batch==8 and sampling.max_new_tokens==128 and sampling.temperature==0 and sampling.top_p==1
            return [['first'],['second']]
    rt=SimpleNamespace(readers=SimpleNamespace(oracle=Oracle()),sweep_batch_size=8)
    h=np.ones((2,5120),np.float32);before=h.copy();x=r.oracle_batch(rt,h,44)
    assert [v['text']for v in x]==['first','second']and np.array_equal(h,before)
    for L in (42,52,60):
        with pytest.raises(ValueError):r.oracle_batch(rt,h,L)

def test_actual168_packet_census_and_batches():
    items,v,m=r.load(ROOT,r.INPUT_SHA)
    assert len(items)==168 and v.shape==(168,5120)and len(list(r.batches(items)))==21
    assert sum(map(len,r.batches(items)))==168 and m['source_items']==84
    assert all(set(x)=={'id','vector_index'}for x in items)
    with pytest.raises(ValueError):r.load(ROOT,'0'*64)

def test_actual_no_labels_and_modified_member_refused(tmp_path):
    shutil.copytree(ROOT,tmp_path/'inputs');p=tmp_path/'inputs/items.json';x=json.loads(p.read_text());x[0]['old_value']='fixture';p.write_text(json.dumps(x))
    with pytest.raises(ValueError):r.load(tmp_path/'inputs',r.INPUT_SHA)

def test_config_original_scope_clock_and_interpretation():
    c=json.loads(Path(__file__).with_name('config.json').read_text())
    assert c['source_items']==84 and c['Oracle_readouts']==168 and c['cap_seconds']==1200 and c['oracle_blocks']==[44]
    assert c['reviewer']=='R-5'and c['judging']['max_USD']==1
