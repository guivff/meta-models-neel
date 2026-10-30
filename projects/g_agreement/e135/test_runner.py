"""Source-only synthetic hook parity, calibration, and sealed input custody."""
import json
from pathlib import Path
import numpy as np
import pytest
import torch
from projects.g_agreement.e127.test_runner import Tiny,Tok,seq
from projects.g_agreement.e128.runner import capture_answer_batch as original_capture
from projects.g_agreement.e135.runner import capture_answer_batch,batches,calibration_records,LAYERS
from projects.g_agreement.e135.inputs import load
from projects.g_agreement.e100.contract import sha,write

ROOT=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e135-dev1-inputs-v1/inputs')

def item(alpha=6,condition='steered'):
    return dict(id='synthetic',base_id='base',row='fact_recall',alpha=alpha,condition=condition,
                ids=seq()[0],read_index=11,candidate_ids=[[[3],[4]]])

@pytest.mark.parametrize('alpha',[6])
@pytest.mark.parametrize('condition',['steered','random'])
def test_identical_E128_forward_capture_answers_and_no_calibration_forward(alpha,condition):
    torch.manual_seed(0);m=Tiny();torch.manual_seed(0);old=Tiny()
    d=np.array([[.2,-.4,.1,.3]],np.float32)*(alpha/8);before=d.copy()
    r=capture_answer_batch(m,Tok(),[item(alpha,condition)],d)
    o=original_capture(old,Tok(),[item(2,condition)],d)
    assert r['answers']==o['answers'] and r['injection_metrics']==o['injection_metrics']
    assert m.calls==old.calls==4 and np.array_equal(before,d)
    for L,h in r['captures'].items():
        assert np.array_equal(h,o['captures'][L])
        assert np.array_equal(h,m.snapshots[1][L][:,11].numpy())
    natural=m.snapshots[0][40][0,:12]
    for state in m.snapshots[1:]:
        diff=state[40][0,:12]-natural
        assert torch.allclose(diff[3:11],torch.from_numpy(d).expand(8,4),atol=1e-6)
        assert torch.equal(diff[[0,1,2,11]],torch.zeros((4,4)))
    assert all(not b._forward_hooks for b in m.layers)
    c=r['calibration'][0]
    assert c['positions']==list(range(3,11)) and c['write_block']==40
    assert np.allclose(c['natural_site_l2'],np.linalg.norm(natural[3:11].numpy().astype(np.float64),axis=-1))
    assert c['composed_delta_l2']==float(np.linalg.norm(d[0].astype(np.float64)))
    assert c['unscaled_d_l2']==c['composed_delta_l2']/6
    assert set(c['reference_delta_l2'])=={'2','4','6','8'}
    for a,n in c['reference_delta_l2'].items():assert np.isclose(n,c['composed_delta_l2']*int(a)/alpha)

@pytest.mark.parametrize('alpha',[2,3,4,5,8])
def test_no_historical_dose_capture(alpha):
    with pytest.raises(ValueError):capture_answer_batch(Tiny(),Tok(),[item(alpha)],np.ones((1,4)))

def test_no_mixed_dose_batch():
    with pytest.raises(ValueError):capture_answer_batch(Tiny(),Tok(),[item(3),item(5)],np.ones((2,4)))

def test_actual_all168_exact_deltas_original_prompts_and_matched_cohort():
    xs,d,m=load(ROOT,sha(ROOT/'INPUT_SEAL.json'))
    source=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops/e104U_test_bind/fact_recall')
    original={x['id']:x for x in json.loads((source/'items.json').read_text())}
    raw=np.load(source/'deltas.npy',allow_pickle=False)
    ptr=json.loads((ROOT.parent/'cpu_only/ORIGINAL_POINTERS.PRIVATE.json').read_text())
    assert len(xs)==len(ptr)==168 and d.shape==(168,5120)
    assert sum(map(len,batches(xs)))==168 and LAYERS==(44,52)
    assert m['total_readouts']==336 and m['steered_readouts']==m['random_readouts']==168
    for x,p in zip(xs,ptr):
        o=original[p['original_item_id']]
        assert x['ids']==o['ids'] and x['read_index']==o['read_index'] and x['candidate_ids']==o['candidate_ids']
        assert np.array_equal(d[x['delta_index']],raw[o['delta_index']]*(x['alpha']/8))
        assert set(x)=={'id','base_id','row','alpha','condition','ids','read_index','candidate_ids','delta_index'}
    for alpha in (6,):
        a={ (x['base_id'],x['condition']):d[x['delta_index']] for x in xs if x['alpha']==alpha }
        for base in {x['base_id'] for x in xs}:
            assert np.isclose(np.linalg.norm(a[base,'steered']),np.linalg.norm(a[base,'random']),rtol=1e-6)

def test_loader_rejects_resealed_changed_prompt(tmp_path):
    import shutil
    p=tmp_path/'inputs';shutil.copytree(ROOT,p)
    xs=json.loads((p/'items.json').read_text());xs[0]['ids'][0]+=1;write(p/'items.json',xs)
    s=json.loads((p/'INPUT_SEAL.json').read_text());s['files']['items.json']=sha(p/'items.json');write(p/'INPUT_SEAL.json',s)
    with pytest.raises(ValueError,match='unchanged matched'):load(p,sha(p/'INPUT_SEAL.json'))

def test_calibration_rejects_nonoriginal_sites_and_nonfinite():
    r=capture_answer_batch(Tiny(),Tok(),[item()],np.ones((1,4),np.float32))
    r['injection_metrics'][0]['injection_sites'][0]['position']=11
    with pytest.raises(ValueError,match='eight'):calibration_records([item()],np.ones((1,4)),r['injection_metrics'])

def test_registered_operator_cap_counts_and_no_judging():
    c=json.loads(Path(__file__).with_name('config.json').read_text())
    assert c['doses']==[6] and c['total_readouts']==336 and not c['labels_on_pod']
    assert c['launch']['cap_seconds']==2880 and c['launch']['creation_cutoff']=='2026-10-30T10:00:00Z'
    assert c['judging']['bank']=='E135' and c['judging']['max_USD']==1 and c['judging']['adapter']=='W-mech2'
