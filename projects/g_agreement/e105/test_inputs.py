import copy
import hashlib
from pathlib import Path
import tarfile
import numpy as np
import pytest
from . import inputs as I
from projects.g_agreement.e101.contract import write,sha


def fixture(monkeypatch):
    monkeypatch.setattr(I,'DIM',4)
    records=[dict(id=f'{i:032x}',label=int(i<42),value='a' if i<42 else 'b',ids=[1,2],candidate_ids=[[[3],[3,4]]]) for i in range(84)]
    h=np.arange(84*4,dtype=np.float32).reshape(84,4)+1
    pairs=[dict(id=x['id'],slot=i,donor_id=records[(i+42)%84]['id'],donor_slot=(i+42)%84) for i,x in enumerate(records)]
    return records,h,pairs


def test_exact_T_same_value_S_no_self_and_reproducible_seed(monkeypatch):
    records,h,pairs=fixture(monkeypatch);f=I.frozen()
    xs,v,s,inv=I.compose('nesting_depth',records,h,pairs,f['scorer_sha256'])
    assert len(xs)==252 and v.shape==(168,4) and len(inv)==84
    assert s==I.same_pairs([x['id'] for x in records],[x['label'] for x in records],[x['value'] for x in records])
    for i in range(84):
        assert np.array_equal(v[2*i],h[pairs[i]['donor_slot']])
        assert np.array_equal(v[2*i+1],h[s[i]['donor_slot']])
        assert s[i]['donor_slot']!=i and records[s[i]['donor_slot']]['label']==records[i]['label']
        assert xs[3*i+2]['vector_index'] is None and xs[3*i+2]['donor_id'] is None
        assert inv[i]['T_label']==1-inv[i]['source_label']==1-inv[i]['S_label']
        assert all(set(x)==I.PUBLIC_FIELDS for x in xs[3*i:3*i+3])


def test_wrong_T_and_missing_same_value_donor_fail(monkeypatch):
    records,h,pairs=fixture(monkeypatch);bad=copy.deepcopy(pairs);bad[0].update(donor_id=records[1]['id'],donor_slot=1)
    with pytest.raises(ValueError,match='other-value'):I.compose('nesting_depth',records,h,bad,'source')
    with pytest.raises(ValueError,match='absent'):I.same_pairs(['one','two'],[0,1],['a','b'])


def test_public_seal_roundtrip_and_private_file_rejection(tmp_path,monkeypatch):
    records,h,t=fixture(monkeypatch);f=I.frozen();xs,v,s,_=I.compose('nesting_depth',records,h,t,f['scorer_sha256'])
    write(tmp_path/'T_PAIRINGS.json',t);write(tmp_path/'S_PAIRINGS.json',s)
    m=dict(experiment='E105',row='nesting_depth',block=44,same_value_seed=I.SEED,behaviour_mode='frozen_continuation',
           baseline_mode='unpatched',frozen_scorer_sha256=f['scorer_sha256'],e100_vector_seal_sha256=I.E100_VECTOR_SHA,
           e100_T_pairings_sha256=sha(tmp_path/'T_PAIRINGS.json'))
    write(tmp_path/'MANIFEST.json',m);write(tmp_path/'items.json',xs);np.save(tmp_path/'vectors.npy',v)
    write(tmp_path/'INPUT_SEAL.json',dict(experiment='E105',labels_on_pod=False,files={n:sha(tmp_path/n) for n in I.PUBLIC_FILES}))
    loaded,states,_=I.load(tmp_path,sha(tmp_path/'INPUT_SEAL.json'));assert loaded==xs and np.array_equal(states,v)
    write(tmp_path/'KEY.json',dict(label=1))
    with pytest.raises(ValueError,match='CPU keys'):I.load(tmp_path,sha(tmp_path/'INPUT_SEAL.json'))


def test_baseline_hook_or_label_leak_and_changed_prompts_rejected(monkeypatch):
    records,h,t=fixture(monkeypatch);xs,v,s,_=I.compose('nesting_depth',records,h,t,'source')
    m=dict(experiment='E105',row='nesting_depth',block=44,same_value_seed=I.SEED,behaviour_mode='frozen_continuation',baseline_mode='unpatched')
    for change in ('label','baseline','prompt','pairing'):
        bad=copy.deepcopy(xs);ss=copy.deepcopy(s)
        if change=='label':bad[0]['true_label']=1
        elif change=='baseline':bad[2]['vector_index']=0
        elif change=='prompt':bad[1]['ids']=[2,2]
        else:ss[0]['donor_slot']=0
        with pytest.raises(ValueError):I.validate(bad,v,m,t,ss)


def test_frozen_scorer_bytes_match_original_seal():
    f=I.frozen();assert f['scorer_sha256']=='1384e98eae4033cb7b2bb7a6e83d48de787168664e63b4d9694c29385be23936'
    assert f['candidate_A_label']==1 and not f['length_normalization']
