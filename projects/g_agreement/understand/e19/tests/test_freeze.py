import json
from pathlib import Path

import numpy as np
import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.e19 import freeze as F


@pytest.fixture
def fixture(tmp_path):
    inputs=tmp_path/'inputs';scores=tmp_path/'scores';oracle=scores/'olens'
    inputs.mkdir();oracle.mkdir(parents=True)
    items=[];labels=[];templates={};index=[]
    rng=np.random.default_rng(1)
    for feature in F.ROWS:
        templates[feature]={'values':['a','b'],'score_orientation':'value_A_positive',
                            'class':'semantic' if feature=='prose_sentiment' else 'state-like'}
        records=[]
        for i in range(168):
            split='dev' if i<84 else 'test'
            item={'id':f'{feature}_{i}','feature':feature,'split':split,'ids':[1,2]}
            items.append(item);records.append(item)
            labels.append({'id':item['id'],'feature':feature,'split':split,'cluster':f'{feature}_{i//14}',
                           'value':'a' if i%2 else 'b'})
        # Test vectors are NaN: any whole-array numerical scan will fail.
        h=np.full((168,64,2,4),np.nan,dtype=np.float32)
        y=np.tile([0,1],42)
        h[:84]=rng.normal(scale=.01,size=(84,64,2,4))
        h[:84,:,:,0]+=(2*y-1)[:,None,None]*3
        name=feature+'.residuals.npy';np.save(oracle/name,h)
        index.append({'feature':feature,'reader':'olens','status':'COMPLETE','n':168,
                      'item_ids':[r['id'] for r in records],'layers':list(range(64)),
                      'positions':['injection','preanswer'],'arrays':{'residuals':name},
                      'array_sha256':{'residuals':P.sha(oracle/name)}})
    source=tmp_path/'mixed-labels.jsonl';P.jsonl(source,labels)
    P.jsonl(inputs/'items.input.jsonl',items);P.dump(inputs/'templates.json',templates)
    P.dump(inputs/'provenance.json',{'experiment':'E3','labels_sha256':P.sha(source)})
    P.seal(inputs,['items.input.jsonl','templates.json','provenance.json'],'INPUTS_FROZEN_E3')
    P.dump(oracle/'index.json',index)
    P.dump(oracle/'provenance.json',{'experiment':'E3','phase':'olens','input_seal_sha256':P.sha(inputs/'INPUT_SEAL.json'),
                                    'source_files':{'synthetic':'0'*64}})
    names=['index.json','provenance.json']+[r['arrays']['residuals'] for r in index]
    P.seal(oracle,names,'SCORES_SEALED_EXPLORATORY_E3')
    P.dump(scores/'provenance.json',{'input_seal_sha256':P.sha(inputs/'INPUT_SEAL.json'),'phases':{'olens':'SEALED'}})
    P.seal(scores,['provenance.json','olens/SCORE_SEAL.json']+['olens/'+n for n in names],'SCORES_SEALED_EXPLORATORY_E3')
    registration=tmp_path/'REGISTRATION.md';registration.write_text('§111 E19 '+' '.join(F.ROWS))
    return inputs,scores,source,registration


def test_middle_third_is_frozen_floor_slice():
    assert F.middle_third_layers()==list(range(21,42))
    assert len(F.middle_third_layers())==21


def test_staging_never_json_decodes_test_labels(fixture,tmp_path,monkeypatch):
    inputs,_,source,_=fixture
    original=F.json.loads
    def guarded(value,*args,**kwargs):
        if isinstance(value,bytes):
            assert b'"split": "test"' not in value
        return original(value,*args,**kwargs)
    monkeypatch.setattr(F.json,'loads',guarded)
    receipt=F.stage_dev_labels(inputs,source,tmp_path/'dev')
    assert receipt['n']==420 and receipt['test_label_records_json_decoded']==0
    assert all(r['split']=='dev' for r in P.rows(tmp_path/'dev/labels.dev.jsonl'))


def test_dev_refit_preserves_raw_coordinates_sigma_and_earliest_tie(monkeypatch):
    rng=np.random.default_rng(9);y=np.tile([0,1],42);groups=np.repeat(np.arange(6),14)
    h=rng.normal(scale=.2,size=(84,64,4)).astype(np.float32)
    h[:,:,0]+=(2*y-1)[:,None]*5
    # Same dev AUROC for every layer -> prospectively specified first-layer tie.
    def tied(x,labels,clusters,**kwargs):
        assert len(x)==84 and len(set(clusters))==6
        return {'auroc':1.,'n':84,'n_clusters':6,'oof_scores':labels.tolist(),'fold_assignment':[0]*84}
    monkeypatch.setattr(F.E3,'grouped_cv_probe',tied)
    meta,u,w,_=F.select_and_refit(h,y,groups)
    assert meta['selected_layer']==21
    assert u[0]>0 and np.linalg.norm(u)==pytest.approx(1)
    np.testing.assert_allclose(u,w/np.linalg.norm(w),rtol=1e-6)
    assert meta['sigma']==pytest.approx(np.std(h[:,21,:].astype(float)@u,ddof=1),rel=1e-6)
    assert meta['orientation_flipped'] is False
    with pytest.raises(ValueError,match='84 finite dev'):
        F.select_and_refit(np.concatenate([h,h]),np.tile(y,2),np.tile(groups,2))


def test_full_freeze_uses_only_dev_vectors_and_loader_binds_hashes(fixture,tmp_path,monkeypatch):
    inputs,scores,source,registration=fixture
    dev=tmp_path/'dev';F.stage_dev_labels(inputs,source,dev)
    calls=[]
    original=F.select_and_refit
    def inspect(h,y,g,**kwargs):
        assert h.shape==(84,64,4) and np.isfinite(h).all()
        calls.append(len(h));return original(h,y,g,**kwargs)
    monkeypatch.setattr(F,'select_and_refit',inspect)
    out=tmp_path/'freeze';cache=tmp_path/'cache'
    receipt=F.freeze_directions(inputs,scores,dev,registration,out,cache)
    assert calls==[84]*5
    assert receipt['test_access']['labels_decoded']==0
    assert receipt['test_access']['residual_items_materialised_for_fit']==0
    loaded,directions=F.load_freeze(out)
    assert set(directions)==set(F.ROWS)
    assert all(d['layer']==21 for d in directions.values())
    assert loaded['directions_sha256']==P.sha(out/'directions.npz')
    assert (cache/'dev_selection_oof.npz').is_file()
    with (out/'directions.npz').open('ab') as handle:handle.write(b'corrupt')
    with pytest.raises(ValueError,match='seal mismatch'):F.load_freeze(out)


def test_test_label_in_derivative_rejected_before_fitting(fixture,tmp_path,monkeypatch):
    inputs,scores,source,registration=fixture
    dev=tmp_path/'dev';F.stage_dev_labels(inputs,source,dev)
    path=dev/'labels.dev.jsonl';rows=P.rows(path);rows[0]['split']='test';path.unlink();P.jsonl(path,rows)
    meta=json.loads((dev/'provenance.json').read_text());meta['dev_labels_sha256']=P.sha(path);P.dump(dev/'provenance.json',meta)
    P.dump(dev/'DEV_LABEL_SEAL.json',{'status':'E19_DEV_LABELS_ONLY','files':{n:P.sha(dev/n) for n in ('labels.dev.jsonl','provenance.json')}})
    calls=[];monkeypatch.setattr(F,'select_and_refit',lambda *a,**k:calls.append(a))
    with pytest.raises(ValueError,match='test label'):
        F.freeze_directions(inputs,scores,dev,registration,tmp_path/'freeze',tmp_path/'cache')
    assert calls==[] and not (tmp_path/'freeze').exists()
