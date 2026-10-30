import pytest
from . import watch as w, adapter as a
from .test_adapter import Fixture
from .test_rules import ORDER


def plan(f,*,gate_shift=2.,include_transplant=True):
    raw=[];native={};transplant={};donors={x['id']:x for x in a.rules.same_condition_pairs(f.cells)}
    token_hash=a.digest([x['candidate_ids'][0] for x in f.defs])
    for x in f.cells:
        i=len(raw);shifts=[1.,2.,-50.,.1] if x['split']=='dev' else [90.,gate_shift,80.,70.]
        raw.append(dict(id=x['id'],block=44,condition='0',contrast_ids=ORDER,candidate_ids_sha256=token_hash,
                        pair_logprobs=[[-1000.+s*x['addressed'],-1000.] for s in shifts]))
        native[x['id']]=dict(seal_index=0,member='raw.json',keys=[i])
        if include_transplant and x['split']=='test' and x['addressed']==0:
            refs={}
            for condition,score in [('T',1.),('S',0.)]:
                i=len(raw)
                raw.append(dict(id=a.measurement_id(x['id'],condition),base_id=x['id'],donor_id=donors[x['id']][condition+'_donor_id'],
                                condition=condition,block=44,contrast_ids=ORDER,candidate_ids_sha256=token_hash,pair_logprobs=[[-1000.+score,-1000.]]*4))
                refs[condition]=dict(seal_index=0,member='raw.json',keys=[i])
            transplant[x['id']]=refs
    source=f.bundle('combined',{'raw.json':raw},experiment='E122',status='COMPLETE',
                    contrast_source_sha256=a.sha(f.cp),source_e85_bank_sha256=a.E85_BANK_SHA)
    index={'native':native}
    if include_transplant:index['transplant']=transplant
    ip=f.bundle('index',{'RAW_INDEX.json':index},experiment='E122',status='SOURCE_POINTERS_ONLY',
                contrast_source_sha256=a.sha(f.cp),source_e85_bank_sha256=a.E85_BANK_SHA,
                source_seals=[dict(seal=str(source),sha256=a.sha(source))])
    return dict(f.base,raw_index_seal=str(ip),raw_index_sha256=a.sha(ip))


def test_combined_acquisition_watcher_once_and_verified_reentry(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);p=plan(f)
    result=w.run(p,'synthetic')
    assert result['status']=='COMPLETE_ALL_PHASES'
    assert a.read(a.CANONICAL/'transplant/RESULTS.json')['fraction_recovered']['estimate']==.5
    monkeypatch.setattr(a.rules,'select_dev',lambda *args:pytest.fail('dev replay'))
    monkeypatch.setattr(a.rules,'native_test',lambda *args:pytest.fail('native replay'))
    monkeypatch.setattr(a.rules,'transplant',lambda *args:pytest.fail('transplant replay'))
    assert w.run(p,'synthetic')==result


def test_failed_gate_never_needs_or_scores_transplant_index(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);p=plan(f,gate_shift=0.,include_transplant=False)
    monkeypatch.setattr(a.rules,'transplant',lambda *args:pytest.fail('b scored after failed gate'))
    result=w.run(p,'synthetic')
    assert result['status']=='COMPLETE_R_BEV1_NOT_MET_B_NOT_RUN'
    assert a.read(a.CANONICAL/'native_test/RESULTS.json')['R_BEV2']=='NOT RUN'
    assert not (a.CANONICAL/'transplant_ONCE.json').exists()


def test_consumed_but_unsealed_guard_never_recovered_implicitly(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);p=plan(f)
    a.CANONICAL.mkdir();a.write(a.CANONICAL/'dev_selection_ONCE.json',dict(failed=True))
    with pytest.raises(FileNotFoundError):w.run(p,'synthetic')


def test_watcher_source_commit_gate_before_plan_read(monkeypatch):
    monkeypatch.setattr(a,'committed',lambda:(_ for _ in ()).throw(ValueError('source not committed')))
    monkeypatch.setattr(a,'read',lambda *args:pytest.fail('plan read before source gate'))
    monkeypatch.setattr('sys.argv',['e122watch','--plan','never'])
    with pytest.raises(ValueError,match='source not committed'):w.main()
