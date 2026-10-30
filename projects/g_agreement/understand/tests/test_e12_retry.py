"""Offline regression for the §99 unknown-path timing failure and NLA-only retry."""
import json
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import e12_retry as R
from projects.g_agreement.understand.cpu import dump,sha,verify


@pytest.fixture
def gate(tmp_path,monkeypatch):
    clock=SimpleNamespace(epoch=1800000000.,mono=100.)
    monkeypatch.setattr(R,'time',SimpleNamespace(time=lambda:clock.epoch,monotonic=lambda:clock.mono))
    monkeypatch.setattr(R,'STOP',clock.epoch+10000);monkeypatch.setattr(R,'ROOT',tmp_path)
    for name in [R.BRIEF,*R.REQUIRED]:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('frozen')
    a={'issuer':'integrator','experiment':'E12','readers':['nla'],'gpu_count':1,'pod_id':'fake',
        'external_hardstop_verified':True,'hold_renewer_verified':True,'brief_registered':True,'brief_pushed':True,
        'brief_sha256':sha(tmp_path/R.BRIEF),'source_files':{n:sha(tmp_path/n) for n in R.REQUIRED},
        'allocated_gpu_seconds':3600.,'previous_gpu_seconds':0.,'provider_created_epoch':clock.epoch-10,
        'setup_deadline_epoch':clock.epoch+2390,'deadline_epoch':clock.epoch+5990,'setup_allowance_seconds':2400.,
        'forecast_method':'all_paths_one_unscored_warmup_plus_three_retained_units'}
    path=tmp_path/'a.json';dump(path,a);g=R.Gate(path,{'nla_native':5,'nla_context':15})
    g.out=tmp_path/'out';g.out.mkdir()
    return g,clock,path


def warm(g):
    for key in R.PATHS:g.warm(key,1.,0)


def test_unknown_paths_never_zero_and_no_bulk_admission(gate):
    g,c,_=gate
    assert g.forecast()['F_seconds'] is None and g.forecast()['science_cap_seconds'] is None
    with pytest.raises(ValueError,match='warm-up'):g.start()
    warm(g);g.start();started=g.started
    for _ in range(3):g.record('nla_native',1.)
    assert g.forecast()['paths']['nla_context']['forecast_seconds'] is None
    assert g.forecast()['F_seconds'] is None
    with pytest.raises(ValueError,match='every path'):g.admit_remaining()
    with pytest.raises(ValueError,match='bulk'):g.record('nla_native',1.)
    for t in [10.,2.,3.]:g.record('nla_context',t)
    report=g.admit_remaining()
    assert report['F_seconds']==50 and report['science_cap_seconds']==435
    assert g.admitted and g.started==started
    c.mono+=1;g.start();assert g.started==started
    verify(g.out,'FORECAST_SEAL.json')
    assert json.loads((g.out/'CLOCK.json').read_text())['unknown_paths_are_zero'] is False


def test_full_forecast_no_fit_is_sealed_before_bulk(gate):
    g,c,_=gate;warm(g);g.start()
    for key in R.PATHS:
        for _ in range(3):g.record(key,200.)
    with pytest.raises(R.NoFit,match='full warmed'):g.admit_remaining()
    assert not g.admitted and g.cap==3600
    verify(g.out,'FORECAST_SEAL.json')
    report=json.loads((g.out/'FULL_WARMED_FORECAST.json').read_text())
    assert report['F_seconds']==4000 and not report['fit']


def test_pilot_counts_science_and_cap_applies_to_same_clock(gate):
    g,c,_=gate;warm(g);g.start();epoch=g.first_science_epoch
    for key in R.PATHS:
        for _ in range(3):g.record(key,1.)
    c.mono+=220
    with pytest.raises(R.NoFit):g.admit_remaining()
    assert g.first_science_epoch==epoch and g.elapsed()==220 and g.cap==390


@pytest.mark.parametrize('bad', [0.,float('nan'),-1.])
def test_bad_timing_is_not_treated_as_zero(gate,bad):
    g,_,_=gate;warm(g);g.start()
    with pytest.raises(ValueError,match='positive'):g.record('nla_native',bad)


def test_setup_and_source_contract(gate):
    g,c,path=gate;a=json.loads(path.read_text())
    for updates in [{'allocated_gpu_seconds':3601},{'previous_gpu_seconds':1},{'setup_allowance_seconds':2401},{'readers':['olens','nla']},{'brief_pushed':False}]:
        dump(path,{**a,**updates})
        with pytest.raises(ValueError):R.Gate(path,g.counts)
    dump(path,a);c.epoch+=2400
    with pytest.raises(TimeoutError,match='setup'):R.Gate(path,g.counts)


def test_collect_nla_only_all_paths_pilot_first_no_duplicate_scores(gate,tmp_path,monkeypatch):
    g,c,_=gate;inp=tmp_path/'input';inp.mkdir()
    items=[{'id':str(i),'feature':'f','text':'source','wrong_activation_index':39-i} for i in range(40)]
    R.jsonl(inp/'items.input.jsonl',items);dump(inp/'templates.json',{'f':{}})
    native=[{'indices':list(range(i,i+8)),'arm':'activation_only'} for i in range(0,40,8)]
    context=[{'indices':u['indices'],'arm':arm,'head_length':7} for arm in ['text_activation','text_only','text_wrong_activation'] for u in native]
    plans={'native':native,'context':context};dump(inp/'nla_units.json',plans);np.save(inp/'acts42.npy',np.ones((40,5120),np.float32))
    nla=tmp_path/'nla';(nla/'av_base').mkdir(parents=True);(nla/'av_base/tokenizer.json').write_text('tok')
    dump(inp/'provenance.json',{'native_carriers':{'nla':{'request':'r','marker_token_id':7,'tokenizer_json_sha256':sha(nla/'av_base/tokenizer.json')}}});dump(inp/'INPUT_SEAL.json',{'files':{}})
    reader=SimpleNamespace(tok=object(),prompt_ids=[1,7,2],marker=1)
    resident=SimpleNamespace(assets={'nla':str(nla)},get=lambda:reader)
    calls=[]
    def score(r,name,u,rs,h,t,s):
        assert r is reader and name=='nla';c.mono+=.01
        key='nla_native' if u['arm']=='activation_only' else 'nla_context'
        calls.append((key,u['arm'],u['indices'][0],g.started is not None,g.admitted))
        return [{'id':rs[i]['id'],'reader':name,'arm':u['arm'],'scores':[i,i],'score':i} for i in u['indices']]
    monkeypatch.setattr(R,'carrier',lambda *a:([1,7,2],1));monkeypatch.setattr(R,'score_unit',score)
    R.collect(SimpleNamespace(inputs=inp),resident,g,g.out)
    assert len(calls)==22 and len([x for x in calls if not x[3]])==2
    pilot=[x for x in calls if x[3] and not x[4]]
    assert [x[0] for x in pilot]==['nla_native']*3+['nla_context']*3
    assert all(x[4] for x in calls[8:])
    final=json.loads((g.out/'nla/provenance.json').read_text());assert final['all_paths_timed_before_bulk']
    scores=[json.loads(s) for s in (g.out/'nla/scores.jsonl').read_text().splitlines()]
    assert len(scores)==160 and len({(r['id'],r['arm']) for r in scores})==160
    assert [r['id'] for r in scores[:40]]==[str(i) for i in range(40)]
    for name in ['nla','nla-native-units','nla-context-units']:verify(g.out/name)
    verify(g.out,'FORECAST_SEAL.json')


def test_loader_calls_only_native_nla_once_and_no_decoder(gate,tmp_path,monkeypatch):
    import common
    from mats.readers import nla
    from projects.g_agreement.blindspot import run
    g,_,_=gate;assets=tmp_path/'assets.json';assets.write_text('{}');calls=[]
    monkeypatch.setattr(run,'_assets',lambda p,n: {'nla':'frozen'} if n==('nla',) else pytest.fail('unneeded model'))
    obj=object()
    def load(**kwargs):calls.append(kwargs);return obj
    monkeypatch.setattr(nla,'load_nla',load)
    r=R.Residents(SimpleNamespace(assets=assets),g)
    assert r.get() is obj;warm(g);g.start();assert r.get() is obj
    assert calls==[{'root':'frozen','load_ar':False}] and r.loads=={'nla_verbalizer':1}
    r.reader=None
    with pytest.raises(RuntimeError,match='load/reload'):r.get()
