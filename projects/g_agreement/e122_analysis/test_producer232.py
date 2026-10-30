from pathlib import Path
import shutil
import pytest
from . import adapter as a, producer232 as p
from .test_adapter import Fixture


def native_fixture(tmp_path, monkeypatch):
    f=Fixture(tmp_path,monkeypatch)
    spec=f.output('dev')
    wrapper=Path(spec['output_seal']);meta=a.read(wrapper)
    source=meta['source_seals'][0];rawseal=Path(source['seal']);raw=a.read(rawseal.parent/'raw.json')
    by_id={x['id']:x for x in f.cells}
    for x in raw:
        x['source_block']=x.pop('block');x['split']=by_id[x['id']]['split']
        for name in ('condition','contrast_ids','candidate_ids_sha256'):x.pop(name)
    a.write(rawseal.parent/'raw.json',raw)
    order=dict(contrasts=f.order,pair_order=['positive','negative'],score='sum natural log probabilities over EVERY candidate token, no mean/no appended EOS')
    a.write(rawseal.parent/'CONTRAST_ORDER.json',order)
    sd=tmp_path/'producer_source';sd.mkdir()
    for label,path in [('operator.py','results/g_agreement/i2/e122_logits232.py'),('scorer.py','projects/g_agreement/e101/acquisition.py')]:shutil.copyfile(a.ROOT/path,sd/label)
    a.core.seal(sd,'SEAL.json')
    monkeypatch.setattr(p,'SOURCE_SHA',a.sha(sd/'SEAL.json'))
    candidates=[x['candidate_ids'][0] for x in f.defs]
    items=[dict(id=x['id'],split=x['split'],block=44,candidate_ids=candidates,ids=[10,20],read_index=1) for x in f.cells]
    ip=f.bundle('public_input',{'items.json':items,'CONTRASTS.json':a.read(f.fp.parent/'CONTRASTS.json')},experiment='E122',part='a',labels_on_pod=False,source_CONTRASTS_SEAL=a.CONTRAST_SHA,items=600,dev=200,test=400,contrasts=4)
    monkeypatch.setattr(p,'INPUT_SHA',a.sha(ip))
    a.core.seal(rawseal.parent,rawseal.name,experiment='E122',part='a',status='COMPLETE',operator_sha256=p.OPERATOR_SHA,original_E105_scorer_sha256=p.SCORER_SHA,input_sha256=p.INPUT_SHA,source_sha256=p.SOURCE_SHA,labels_cpu_only=True,T_S_transplants_invoked=False,readout_or_judging_calls=0)
    source.update(sha256=a.sha(rawseal),format='i2_e122_logits232_v1',producer_input_seal=str(ip),producer_source_seal=str(sd/'SEAL.json'))
    files=meta.pop('files');a.core.seal(wrapper.parent,wrapper.name,**meta)
    spec['output_sha256']=a.sha(wrapper)
    return f,spec,ip,rawseal


def test_original_i2_envelope_without_raw_rewrite(tmp_path,monkeypatch):
    f,spec,_,rawseal=native_fixture(tmp_path,monkeypatch)
    before=a.sha(rawseal.parent/'raw.json')
    rows=a.measurements(spec,'dev',f.fp,f.cells,f.defs)
    assert len(rows)==200 and rows[1]['scores']['self']==2
    assert a.sha(rawseal.parent/'raw.json')==before


def test_wrong_original_i2_split_rejected_before_guard(tmp_path,monkeypatch):
    f,spec,_,rawseal=native_fixture(tmp_path,monkeypatch)
    raw=a.read(rawseal.parent/'raw.json');raw[0]['split']='test';a.write(rawseal.parent/'raw.json',raw)
    meta=a.read(rawseal);meta.pop('files');a.core.seal(rawseal.parent,rawseal.name,**meta)
    wrapper=Path(spec['output_seal']);meta=a.read(wrapper);meta['source_seals'][0]['sha256']=a.sha(rawseal);meta.pop('files');a.core.seal(wrapper.parent,wrapper.name,**meta);spec['output_sha256']=a.sha(wrapper)
    with pytest.raises(ValueError,match='identity/site/split'):a.execute(spec,'select-dev','synthetic-commit')
    assert not (a.CANONICAL/'dev_selection_ONCE.json').exists()
