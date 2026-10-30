from copy import deepcopy
from pathlib import Path
import pytest
from . import adapter as a,rules as r,screen,transport
from projects.g_agreement.e133_analysis.test_rules import pairs as old_pairs
from projects.g_agreement.e133_analysis.test_adapter import fixture as old_fixture


def probe(current44=.7):
    return dict(layers={str(l):dict(current=dict(groups=dict(multi_hop_test=dict(macro_ovr_AUROC=current44 if l==44 else .9))))for l in (36,44,48,52,56,60)})


def test_rnl2_all_original_gates_only_d1_and_readings_separate(monkeypatch):
    xs=old_pairs(30,0)
    for p in xs:p['kind']='D1'
    d2=deepcopy(xs)
    for p in d2:
        p['kind']='D2';p['pair_id']='D2:'+p['pair_id']
        for m in p['members']:m['readouts'][44]={k:int(k=='current')for k in m['readouts'][44]}
    monkeypatch.setattr(r.probes,'analyze',lambda *args:probe())
    z,_=r.analyze(xs+d2,['Erin','Dana','Carl'],draws=20)
    assert z['R_NL2']=='MET'and z['subdesigns']['D2']['full_R_NL1_structure']['R_NL1']=='NOT MET'
    assert z['subdesigns']['D1']['readings']['a_timing']=='MET'
    assert z['subdesigns']['D2']['readings']['c_faithful_early']=='MET'
    for p in xs:
        for m in p['members']:m['patches'][60]['earlier_token']=m['own_logodds']+.16*(-2*m['own_logodds'])
    assert r.analyze(xs+d2,['Erin','Dana','Carl'],draws=20)[0]['R_NL2']=='NOT MET'


def test_confidence_boundary_and_fewer30_no_confirmatory(monkeypatch):
    stat=lambda v,lo:dict(estimate=v,Wilson95=[lo,1])
    reads={'44':{'previous':stat(.3,.2),'current':stat(.4,.3)},'60':{'current':stat(.7,.6)}}
    ps={b:{c:dict(estimate=.15,CI95=[0,1])for c in r.PATCHES}for b in r.BLOCKS};ps[52]['read_token']=dict(estimate=.5,CI95=[.25001,.9])
    assert r.base.classify(reads,ps,True)['R_NL1']=='NOT MET'
    reads['44']['previous']['Wilson95'][0]=.20001
    assert r.base.classify(reads,ps,True)['R_NL1']=='MET'
    ps[52]['read_token']['CI95'][0]=.25
    assert r.base.classify(reads,ps,True)['R_NL1']=='NOT MET'
    xs=old_pairs(29,0)
    for p in xs:p['kind']='D1'
    monkeypatch.setattr(r.probes,'analyze',lambda *args:probe())
    assert r.analyze(xs,['Erin','Dana','Carl'],draws=10)[0]['R_NL2']=='DESCRIPTIVE ONLY'


def test_reporting_and_faithful_descriptions_use_registered_points():
    rr={'44':{'current':{'estimate':.2},'previous':{'estimate':.3}},'60':{'current':{'estimate':.5}}}
    ps={b:{'read_token':{'estimate':.5 if b in(52,56)else .15}}for b in r.BLOCKS}
    z=r.readings(dict(reader_rates=rr,patches=ps),probe(.9),True)
    assert z['b_reporting']=='MET'and z['c_faithful_early']=='NOT MET'
    rr['44']['current']['estimate']=.7
    assert r.readings(dict(reader_rates=rr,patches=ps),probe(.9),True)['c_faithful_early']=='MET'


def test_first42_each_and16_onehop_unchanged_classifier():
    pairs=[];answers={}
    for kind,count in [('D1',45),('D2',45),('one_hop',20)]:
        for j in range(count):
            ms=[dict(member=k,item_id=f'{kind}:{j}:{k}',current=c,previous='Dana')for k,c in enumerate(['Erin','Carl'])]
            pairs.append(dict(pair_id=f'{kind}:{j}',kind=kind,generation_index=j,members=ms))
            for m in ms:answers[m['item_id']]=dict(id=m['item_id'],text=m['current'],token_ids=[1],greedy_max_new_tokens=32)
    z=screen.select(pairs,answers)
    assert {k:len(v)for k,v in z['selected'].items()}==dict(D1=42,D2=42,one_hop=16)
    assert not z['screen_only']and z['selected']['D2'][-1]=='D2:41'


def synthetic_transport(tmp_path,monkeypatch):
    spec,source=old_fixture(tmp_path,monkeypatch);monkeypatch.setattr(a,'GUARD',tmp_path/'E137_ONCE.json')
    ip=Path(spec['inventory_seal']);pairs=a.core.read(ip.parent/'PAIRS.PRIVATE.json');kinds={'0':'D1','1':'D2','2':'one_hop'}
    for p in pairs:
        p['kind']=kinds[p['pair_id']]
        for m in p['members']:m['latest_mention']='Dana'
    rows=a.core.read(source.parent/'original.json')
    for row in rows:row['identity']['kind']=kinds[row['identity']['pair_id']]
    a.core.write(source.parent/'original.json',rows);meta=a.core.read(source);meta.pop('files');meta['experiment']='E137';a.core.seal(source.parent,source.name,**meta)
    op=Path(spec['output_seal']);meta=a.core.read(op);meta.pop('files');meta.update(experiment='E137',judging_bank='E137',judging_cap_usd=2,source_seals=[dict(seal=str(source),sha256=a.core.sha(source))]);a.core.seal(op.parent,op.name,**meta);spec['output_sha256']=a.core.sha(op);spec['native_output_sha256']=a.core.sha(source)
    return spec,pairs


def test_full_original_pointer_transport_main_guard_no_replay(tmp_path,monkeypatch):
    spec,pairs=synthetic_transport(tmp_path,monkeypatch)
    monkeypatch.setattr(a,'metadata',lambda s:(pairs,['Erin','Dana','Carl','Evan']))
    from . import probe_phase
    monkeypatch.setattr(probe_phase,'fit',lambda *args:dict(subdesigns={d:dict(probes=probe())for d in('D1','D2')}))
    out=a.run(spec,'synthetic-only');z=a.core.read(out.parent/'RESULTS.json')
    assert z['experiment']=='E137'and z['R_NL2']=='DESCRIPTIVE ONLY'and set(z['subdesigns'])=={'D1','D2'}
    assert (out.parent/'PER_PAIR.PRIVATE.json').stat().st_mode&0o777==0o600
    with pytest.raises(ValueError,match='once guard'):a.run(spec,'synthetic-only')


def test_changed_required_recipient_contrast_is_rejected(tmp_path,monkeypatch):
    spec,pairs=synthetic_transport(tmp_path,monkeypatch);pairs[0]['recipient_contrast_sha256']='changed'
    with pytest.raises(ValueError,match='ordered recipient contrast'):transport.inputs(spec,pairs)


def test_metadata_full_per_design_frozen_selection(tmp_path,monkeypatch):
    spec,pairs=synthetic_transport(tmp_path,monkeypatch)
    # Metadata-only fixture: full candidate proof and 30 frozen pairs/design.
    selected=[];proof=dict(classifier_sha256=screen.MATCHER_SHA256,selected={k:[]for k in screen.KINDS},screening=[])
    for kind,n in [('D1',150),('D2',150),('one_hop',60)]:
        for j in range(n):
            pid=f'{kind}:{j}';correct=j<30 if kind!='one_hop'else j<2
            proof['screening'].append(dict(pair_id=pid,kind=kind,generation_index=j,correct_both=correct))
            if correct:
                p=deepcopy(pairs[0]);p.update(pair_id=pid,kind=kind,generation_index=j);selected.append(p);proof['selected'][kind].append(pid)
    inv=Path(spec['inventory_seal']);old=a.core.read(inv);sp=Path(old['screen_seal']);a.core.write(sp.parent/'SCREEN_SELECTION.PRIVATE.json',proof);m=a.core.read(sp);m.pop('files');a.core.seal(sp.parent,sp.name,**m)
    a.core.write(inv.parent/'PAIRS.PRIVATE.json',selected);old.pop('files');old.update(experiment='E137',screen_sha256=a.core.sha(sp));a.core.seal(inv.parent,inv.name,**old);spec['inventory_sha256']=a.core.sha(inv)
    spec['e133_main_seal']=str(sp);monkeypatch.setattr(a,'E133_MAIN_SHA',a.core.sha(sp))
    got,_=a.metadata(spec);assert len(got)==62
    selected[0]['members'][0]['latest_mention']=selected[0]['members'][0]['current'];a.core.write(inv.parent/'PAIRS.PRIVATE.json',selected);old=a.core.read(inv);old.pop('files');a.core.seal(inv.parent,inv.name,**old);spec['inventory_sha256']=a.core.sha(inv)
    with pytest.raises(ValueError,match='most-recent'):a.metadata(spec)
