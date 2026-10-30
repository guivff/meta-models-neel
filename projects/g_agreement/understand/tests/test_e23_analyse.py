from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import e23 as E,e23_analyse as A
from projects.g_agreement.understand.cpu import dump,sha,seal,verify,read
from projects.g_agreement.understand.followup_packed import jsonl


def test_synthetic_full_report_all_cells_controls_and_once_guard(tmp_path,monkeypatch):
    inp=tmp_path/'inputs';col=tmp_path/'collection';inp.mkdir();col.mkdir();(col/'continuations').mkdir()
    rng=np.random.default_rng(2);items=[];labels=[];cont=[]
    for dataset,features in [('O',E.FEATURES),('S',E.FEATURES[:3])]:
        for feature in features:
            for split in ('dev','test'):
                for j in range(20):
                    key=f'{dataset}-{feature}-{split}-{j}';y=j%2;text='inside A' if y else 'outside B'
                    items.append({'id':key,'set':dataset,'feature':feature,'split':split,'ids':[1,2], 'P32':text,'Pfull':text})
                    labels.append({'id':key,'set':dataset,'feature':feature,'split':split,'cluster':key if dataset=='S' else f'{feature}-{split}-{j//2}','y':y})
                    cont.append({'id':key,'ids':[3]*16,'text':text})
    private=tmp_path/'labels.jsonl';jsonl(private,labels)
    jsonl(inp/'items.input.jsonl',items);dump(inp/'provenance.json',{'private_sha256':sha(private)})
    donors=E.donor_maps([{**r,'y':s['y']} for r,s in zip(items,labels)]);dump(inp/'donors.json',donors)
    np.savez(inp/'W1.directions.npz',**{f:np.array([1.,0.,0.,0.]) for f in E.FEATURES})
    seal(inp,[p.name for p in inp.iterdir()],'SYNTHETIC');(inp/'SCORE_SEAL.json').rename(inp/'INPUT_SEAL.json')
    x=rng.normal(0,.1,(len(items),4)).astype(np.float32);x[:,0]=np.array([r['y'] for r in labels])*2-1
    np.save(col/'S.acts44.npy',x[[i for i,r in enumerate(items) if r['set']=='S']])
    for layer in E.LAYERS:
        for arm in E.UNIQUE_ARMS:np.save(col/f'ar_{layer}_{arm}.npy',x)
    for layer in (42,44):
        for phrasing in ('W1','Suraj'):
            jsonl(col/f'asked_{layer}_{phrasing}.jsonl',[{'id':r['id'],'set':r['set'],'score':float(x[i,0])} for i,r in enumerate(items) if r['split']=='test' and r['feature']=='table_column'])
    jsonl(col/'continuations/continuations.jsonl',cont);seal(col/'continuations',['continuations.jsonl'],'E23_ALL_F16_FROZEN_BEFORE_ANY_AR')
    ap=tmp_path/'assignment.json';dump(ap,{'source_files':{}})
    dump(col/'run.json',{'status':'COMPLETE','input_seal_sha256':sha(inp/'INPUT_SEAL.json'),'assignment_sha256':sha(ap)})
    dump(col/'PARITY.json',{'all_items_all_layers':True})
    dump(col/'FORECAST_SEAL.json',{'files':{}})
    seal(col,[str(p.relative_to(col)) for p in col.rglob('*') if p.is_file()],'E23_COMPLETE')
    monkeypatch.setattr(A,'BOOT',8);contrast=A.linear_contrast
    monkeypatch.setattr(A,'linear_contrast',lambda terms,labels:contrast(terms,labels,n_boot=8))
    args=SimpleNamespace(inputs=inp,collection=col,labels=private,assignment=ap,out=tmp_path/'analysis')
    A.analyse(args)
    verify(args.out);m=read(args.out/'metrics.json')
    assert len(m['rows'])==8*2*5*3
    assert len(m['E23b']['cells'])==8
    assert len(m['W1_transfer_secondary'])==3*2*5
    assert len(m['setS_probe_fits'])==3
    assert all(r['contract']=='off-contract' for r in m['rows'] if r['arm'] in ('P32','Pfull'))
    assert all(r['prediction_met'] for r in m['Swap_secondary'])
    assert all(r['fit_split']=='dev' and not r['orientation_flipped'] for r in m['setS_probe_fits'].values())
    original=sha(args.out/'SCORE_SEAL.json')
    with pytest.raises(FileExistsError):A.analyse(args)
    assert sha(args.out/'SCORE_SEAL.json')==original
