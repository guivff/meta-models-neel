from copy import deepcopy
from pathlib import Path
import numpy as np
import pytest
from . import adapter as a,probe_phase as p,probes,rules
from .test_adapter import synthetic_transport,probe


def lifecycle(tmp,monkeypatch):
    spec,pairs=synthetic_transport(tmp,monkeypatch)
    monkeypatch.setattr(a,'metadata',lambda s:(pairs,['Erin','Dana','Carl','Evan']))
    monkeypatch.setattr(p,'native_metadata',lambda s:{})
    def vectors(spec,inventory,seal):
        data=deepcopy(inventory)
        for pair in data:
            for m in pair['members']:m['vectors']={l:[float(m['member']),1.]for l in probes.LAYERS}
        return data
    monkeypatch.setattr(p,'native_vectors',vectors)
    monkeypatch.setattr(p,'fit',lambda *args:dict(subdesigns={d:dict(probes=probe())for d in('D1','D2')}))
    return spec


def test_probe_phase_independent_main_reuses_once_without_second_fit(tmp_path,monkeypatch):
    spec=lifecycle(tmp_path,monkeypatch);seal=p.run(spec,'synthetic-only');before=seal.read_bytes()
    assert not a.GUARD.exists()and p.paths()[0].exists()
    def fail(*args):pytest.fail('second fit after completed probe-only phase')
    monkeypatch.setattr(p,'fit',fail);monkeypatch.setattr(rules.probes,'analyze',fail)
    result=a.run(spec,'synthetic-main');assert a.core.read(result.parent/'RESULTS.json')['experiment']=='E137'
    assert before==seal.read_bytes()
    assert (seal.parent/'FIT_EVIDENCE.PRIVATE.json').stat().st_mode&0o777==0o600
    with pytest.raises(ValueError,match='once guard'):p.run(spec,'repeat')


def test_failed_phase_retains_guard_blocks_main_before_claim(tmp_path,monkeypatch):
    spec=lifecycle(tmp_path,monkeypatch)
    def fail(*args):raise ValueError('synthetic bad vector identity')
    monkeypatch.setattr(p,'native_vectors',fail)
    with pytest.raises(ValueError,match='bad vector'):p.run(spec,'synthetic')
    assert p.paths()[0].exists()and not a.GUARD.exists()
    with pytest.raises(ValueError,match='in progress/failed'):a.run(spec,'synthetic')
    assert not a.GUARD.exists()


def test_foreign_native_capture_cannot_reuse_probe_seal(tmp_path,monkeypatch):
    spec=lifecycle(tmp_path,monkeypatch);p.run(spec,'synthetic')
    with pytest.raises(ValueError,match='same frozen'):p.existing(spec['inventory_sha256'],'other')


def vectors(n,kind):
    pairs=[]
    for i in range(n):
        ms=[]
        for j in(0,1):
            current=['A','B','E'][(i+j)%3];previous=['C','D'][i%2]
            v=[float(current=='A'),float(current=='B'),float(previous=='C'),float(j)]
            ms.append(dict(member=j,item_id=f'{kind}:{i}:{j}',current=current,previous=previous,vectors={l:v for l in probes.LAYERS}))
        pairs.append(dict(pair_id=f'{kind}:{i}',kind=kind,generation_index=i,members=ms))
    return pairs


def test_d1_42_real_fixed_fits_saved_once_d2_19_stays_descriptive_ne():
    audit=[];result=p.fit(vectors(42,'D1')+vectors(19,'D2')+vectors(16,'one_hop'),['A','B','C','D','E'],audit)
    assert result['subdesigns']['D1']['eligible']and not result['subdesigns']['D2']['eligible']
    assert result['subdesigns']['D2']['scope']=='DESCRIPTIVE ONLY'
    assert len(audit)==18 and all(x['subdesign']=='D1'for x in audit)
    for layer in probes.LAYERS:
        d1=result['subdesigns']['D1']['probes']['layers'][str(layer)]
        d2=result['subdesigns']['D2']['probes']['layers'][str(layer)]
        assert all(x['dev_pairs']==30 and x['test_pairs']==12 for x in d1.values())
        assert all(x['status']=='NOT EVALUABLE'and x['dev_pairs']==19 for x in d2.values())
    for x in audit:
        assert len(x['dev_pair_ids'])==30 and len(x['test_pair_ids'])==12
        assert set(x['dev_pair_ids']).isdisjoint(x['test_pair_ids'])
        assert len(x['coefficients'])==len(x['intercepts'])and x['predictions']['multi_hop_test']['probabilities']
        # Original saved coefficients/intercepts reconstruct once-produced test scores.
        lookup={m['item_id']:m for pair in vectors(42,'D1')+vectors(16,'one_hop')for m in pair['members']}
        for saved in x['predictions'].values():
            xx=np.asarray([lookup[i]['vectors'][x['layer']]for i in saved['item_ids']])
            logits=xx@np.asarray(x['coefficients']).T+np.asarray(x['intercepts'])
            if len(x['classes'])==2:
                positive=1/(1+np.exp(-logits[:,0]));scores=np.column_stack([1-positive,positive])
            else:
                exp=np.exp(logits-logits.max(axis=1,keepdims=True));scores=exp/exp.sum(axis=1,keepdims=True)
            assert np.allclose(scores,saved['probabilities'],rtol=0,atol=1e-12)


def native_fixture(tmp):
    root=tmp/'native';(root/'main_synthetic').mkdir(parents=True)
    pairs=vectors(2,'D1');rows=[];records=[];arr=[]
    for pair in pairs:
        for m in pair['members']:
            ix=len(records);records.append(dict(id=m['item_id'],pair_id=pair['pair_id'],member=m['member'],family='multi_hop'))
            arr.append([float(ix),2.]);rows.append(dict(id=m['item_id'],kind='capture_answer',member='capture.json',record=ix,layers={str(l):dict(member='vectors.npy',index=ix)for l in probes.LAYERS}))
    a.core.write(root/'main_synthetic/capture.json',records);a.core.write(root/'main_synthetic/INDEX.json',rows);np.save(root/'main_synthetic/vectors.npy',np.asarray(arr,dtype=np.float32))
    a.core.seal(root,'OUTPUT_SEAL.json',experiment='E137',status='COMPLETE',labels_cpu_only=True,stages=dict(main_synthetic='COMPLETE'))
    spec=dict(native_output_seal=str(root/'OUTPUT_SEAL.json'),native_output_sha256=a.core.sha(root/'OUTPUT_SEAL.json'))
    ip=tmp/'inventory.json';a.core.write(ip,dict(native_output_sha256=spec['native_output_sha256']));spec['inventory_seal']=str(ip)
    return spec,pairs


def test_literal_native_index_vector_members_and_identity_no_judging(tmp_path):
    spec,pairs=native_fixture(tmp_path);seal=p.native_metadata(spec);data=p.native_vectors(spec,pairs,seal)
    assert len(data)==2 and data[1]['members'][1]['vectors'][44]==[3.,2.]
    pairs[0]['pair_id']='wrong'
    with pytest.raises(ValueError,match='literal native'):p.native_vectors(spec,pairs,seal)


def test_original_native_hash_and_complete_stage_fail_closed(tmp_path):
    spec,pairs=native_fixture(tmp_path);spec['native_output_sha256']='different'
    with pytest.raises(ValueError,match='inventory-bound'):p.native_metadata(spec)
