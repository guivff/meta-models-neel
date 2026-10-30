from copy import deepcopy
import pytest
from . import adapter as a
from projects.g_agreement.e128_analysis.test_coordinator import pairs
from projects.g_agreement.e127_analysis.test_rules import code

def records():
    xs=pairs((0,42,84))
    for x in xs:x['doses']={6:deepcopy(x['doses'][8])}
    for x in xs:
        for ds in x['doses'].values():
            for z in ds.values():z['answer']='old'
    return xs

def rawcal():
    return dict(block=40,positions='eight_before_read',unsteered=True,cells=[dict(item_id=str(i),dose=d,condition=c,write_positions=list(range(8)),natural_site_l2=[10.]*8,composed_delta_l2=float(d*2)) for i in range(84) for d in a.DOSES for c in a.CONDITIONS])

def test_calibration_ratio_exact_historical_no_reruns():
    r=a.calibration(rawcal(),{str(i) for i in range(84)})
    assert r['n_positions']==672 and r['raw_cells_checked']==168
    assert r['ratios']['8']['steered']==1.6 and r['ratios']['6']['steered']==1.2 and set(r['ratios'])=={'2','4','6','8'}

@pytest.mark.parametrize('field,value',[('natural_site_l2',[11.]*8),('composed_delta_l2',99.),('write_positions',[0]*8)])
def test_calibration_rejects_changed_repeats(field,value):
    data=rawcal();data['cells'][2 if field=='composed_delta_l2' else 1][field]=value
    with pytest.raises(ValueError):a.calibration(data,{str(i) for i in range(84)})

def test_exact_grid_rejects_duplicate_calibration():
    data=rawcal();data['cells'][-1]=data['cells'][0]
    with pytest.raises(ValueError,match='exact168'):a.calibration(data,{str(i) for i in range(84)})

def test_rates_fixed_cohort_and_missing_semantics():
    xs=records();xs[0]['doses'][6]['steered']['oracle'][44]=code(None,'UNPARSEABLE')
    xs[1]['doses'][6]['steered']['oracle'][44]=code(None)
    cal=a.calibration(rawcal(),{x['item_id'] for x in xs})
    r=a.analyze(xs,{str(i) for i in range(42)},cal)
    z=r['doses']['6']['cohorts']['fixed_alpha4_42']['steered']['44']
    assert z['rates']['old']['k']==40 and z['rates']['old']['n']==41
    assert z['rates']['neither']['k']==1 and z['rates']['neither']['missing_n']==1
    assert r['confirmatory_rule'] is None and set(r['doses'])=={'6'}
    assert r['doses']['6']['cohorts']['own_flipped']['random']['44']['planned_n']==84

def test_gpu_only_preserves_calibration_and_flips():
    xs=records()
    for x in xs:
        for ds in x['doses'].values():
            for z in ds.values():z['oracle']={44:None,52:None}
    r=a.analyze(xs,{str(i) for i in range(42)},a.calibration(rawcal(),{x['item_id'] for x in xs}))
    assert r['doses']['6']['flip_rates']['steered']['k']==84
    assert r['doses']['6']['cohorts']['fixed_alpha4_42']['steered']['44']['rates']['old']['estimate'] is None
    assert r['doses']['6']['calibration_ratio']['steered']==1.2

def test_replay_refused_before_inputs(tmp_path,monkeypatch):
    monkeypatch.setattr(a,'CUSTODY',tmp_path);(tmp_path/'ANALYSIS_ONCE.json').write_text('{}')
    with pytest.raises(ValueError,match='guard consumed'):a.run({},'synthetic')

def test_source_gate_precedes_spec(monkeypatch):
    import sys
    monkeypatch.setattr(sys,'argv',['adapter','--spec','no-input'])
    def fail(*args):raise ValueError('uncommitted')
    monkeypatch.setattr(a.t,'committed',fail)
    monkeypatch.setattr(a.t.core,'read',lambda *args:pytest.fail('opened input'))
    with pytest.raises(ValueError,match='uncommitted'):a.main()

def fixture(tmp,judging='COMPLETE'):
    from . import transport as tr
    core=a.t.core;items=[];measurements=[];source=[]
    def pointer(row,key):return dict(seal_index=0,member='raw.json',keys=[row,key])
    for i in range(84):
        item=dict(item_id=str(i),old_value='A',new_value='B',candidate_strings={'old':'Paris','new':'London'});items.append(item)
        doses={}
        for dose in a.DOSES:
            doses[str(dose)]={}
            for c in a.CONDITIONS:
                identity=dict(item_id=str(i),condition=c,dose=dose,classifier_sha256=a.t.MATCHER_SHA256,raw_id=f'{i}-{dose}-{c}')
                rec=dict(id=identity['raw_id'],text='London',token_ids=[1],greedy_max_new_tokens=3,pair_logits=[[1,5]])
                ix=len(source);source.append(dict(identity=identity,record=rec));beh=dict(identity=pointer(ix,'identity'),record=pointer(ix,'record'))
                oracle={}
                for l in a.LAYERS:
                    jid=f'{i}-{dose}-{c}-{l}';ident=dict(item_id=str(i),row='fact_recall',condition=c,dose=dose,layer=l,reader='oracle',judgment_id=jid)
                    z=code('A' if l==44 else 'B');z['id']=jid;z['evidence']=z['values'][0]
                    ix=len(source);source.append(dict(identity=ident,code=z,text='A B'))
                    oracle[str(l)]=None if judging=='NOT RUN' else dict(identity=pointer(ix,'identity'),code=pointer(ix,'code'),text=pointer(ix,'text'))
                doses[str(dose)][c]=dict(behaviour=beh,oracle=oracle)
        measurements.append(dict(item_id=str(i),doses=doses))
    src=tmp/'source';src.mkdir();core.write(src/'raw.json',source);core.seal(src,'SEAL.json',experiment='E135',status='COMPLETE')
    out=tmp/'output';out.mkdir();core.write(out/'MEASUREMENTS.json',measurements)
    meta=dict(experiment='E135',status='COMPLETE',inventory_sha256='synthetic',judging_bank='E135',judging_cap_usd=1,lifetime_booked_usd=0,unknown_charge_requests=0,judging_status=judging,rubric_sha256=tr.RUBRIC_SHA,route_verified=True,labels_cpu_only=True,redaction_audit_complete=True,redacted_count=0,layers=[44,52],new_doses=[6],steer=dict(block=40,positions='eight_before_read',direction='class_mean'),behaviour_classifier_sha256=a.t.MATCHER_SHA256,source_seals=[dict(seal=str(src/'SEAL.json'),sha256=core.sha(src/'SEAL.json'))])
    core.seal(out,'SEAL.json',**meta)
    spec=dict(output_seal=str(out/'SEAL.json'),output_sha256=core.sha(out/'SEAL.json'),inventory_sha256='synthetic')
    return spec,items,meta

@pytest.mark.parametrize('judging',['COMPLETE','NOT RUN'])
def test_full336_transport_and_gpu_only(tmp_path,judging):
    spec,items,meta=fixture(tmp_path,judging)
    xs=a.inputs(spec,'E135',items,{},meta,pair_answer_fn=a.d.pair_answer)
    assert len(xs)==84 and sum(len(z['oracle']) for x in xs for ds in x['doses'].values() for z in ds.values())==336
    assert xs[0]['doses'][6]['steered']['pair_preference_flip_descriptive'] is True
    assert (xs[0]['doses'][6]['steered']['oracle'][44] is None)==(judging=='NOT RUN')
    cal=a.calibration(rawcal(),{x['item_id'] for x in xs})
    assert a.analyze(xs,{str(i) for i in range(42)},cal)['doses']['6']['flip_rates']['steered']['k']==84

def test_source_evidence_mismatch_stops(tmp_path):
    spec,items,meta=fixture(tmp_path)
    from pathlib import Path
    core=a.t.core;s=Path(meta['source_seals'][0]['seal']);raw=core.read(s.parent/'raw.json');raw[1]['code']['evidence']='not in original';core.write(s.parent/'raw.json',raw)
    core.seal(s.parent,s.name,experiment='E135',status='COMPLETE');meta['source_seals'][0]['sha256']=core.sha(s)
    out=Path(spec['output_seal']);core.seal(out.parent,out.name,**meta);spec['output_sha256']=core.sha(out)
    with pytest.raises(ValueError,match='evidence substring'):a.inputs(spec,'E135',items,{},meta,pair_answer_fn=a.d.pair_answer)

def test_calibration_literal_source_binding(tmp_path):
    core=a.t.core;raw=dict(base='0',alpha=6,condition='steered',positions=list(range(8)),natural_site_l2=[10.]*8,composed_delta_l2=12.)
    core.write(tmp_path/'raw.json',[raw]);core.seal(tmp_path,'SEAL.json',experiment='E135',status='COMPLETE')
    cell=rawcal()['cells'][0];cell['source_ref']=dict(seal_index=0,member='raw.json',keys=[0],original_item_id_field='base',field_mapping=dict(dose='alpha',condition='condition',write_positions='positions',natural_site_l2='natural_site_l2',composed_delta_l2='composed_delta_l2'))
    meta=dict(source_seals=[dict(seal=str(tmp_path/'SEAL.json'),sha256=core.sha(tmp_path/'SEAL.json'))]);data=dict(cells=[cell])
    assert a.calibration_sources(data,meta)==data
    cell['composed_delta_l2']=7.
    with pytest.raises(ValueError,match='captured fields'):a.calibration_sources(data,meta)

def test_split_is_disjoint_and_preserves_fixed_cohort_and_random_ids():
    xs=records();fixed={str(i) for i in range(42)}
    for x in xs:
        i=int(x['item_id'])
        x['doses'][6]['steered']['pair_preference_flip_descriptive']=None if i==83 else i>=10
        x['doses'][6]['random']['pair_preference_flip_descriptive']=False
    r=a.analyze(xs,fixed,a.calibration(rawcal(),{x['item_id'] for x in xs}))['doses']['6']['cohorts']
    for c in a.CONDITIONS:
        assert r['fixed_alpha4_42'][c]['44']['planned_n']==42
        assert r['alpha6_flipped_in_alpha4_cohort'][c]['44']['planned_n']==32
        assert r['newly_flipped_alpha6'][c]['44']['planned_n']==41
        assert r['own_flipped'][c]['44']['planned_n']==73

@pytest.mark.parametrize('field,value',[('new_doses',[3,5,6]),('judging_cap_usd',2)])
def test_superseded_doses_and_cap_rejected(tmp_path,field,value):
    from pathlib import Path
    spec,items,meta=fixture(tmp_path);meta[field]=value
    seal=Path(spec['output_seal']);a.t.core.seal(seal.parent,seal.name,**meta)
    spec['output_sha256']=a.t.core.sha(seal)
    with pytest.raises(ValueError):a.inputs(spec,'E135',items,{},meta,pair_answer_fn=a.d.pair_answer)


def test_deviation1_input_pin_rejects_superseded_package():
    a.verify_input_pin(dict(source_input_sha256='381b58bde8ab7031e7a1de07bec1afe05655010a815e61a1a84c3b689c1c8047'))
    with pytest.raises(ValueError):
        a.verify_input_pin(dict(source_input_sha256='882ddcaaefbe14cfee0b8afb3c2377fab942aa38bf439cab8db88aff89338f45'))

@pytest.mark.parametrize('drift',[None,'alias','pointer_id','cohort','wrong_item_field','dose','condition','scale','input_pin'])
def test_calibration_acquisition_alias_map(tmp_path,monkeypatch,drift):
    core=a.t.core
    acq=tmp_path/'acq';ptrdir=tmp_path/'ptr';native=tmp_path/'native'
    for p in (acq,ptrdir,native):p.mkdir()
    acquired=dict(id='alias:6:steered',base_id='alias',alpha=6,condition='steered')
    core.write(acq/'items.json',[acquired]);core.seal(acq,'INPUT_SEAL.json',experiment='E135')
    pin=core.sha(acq/'INPUT_SEAL.json')
    monkeypatch.setattr(a,'verify_input_pin',lambda m:a.require(m['source_input_sha256']==pin,'test original input pin'))
    original=dict(id=acquired['id'],original_base_id='0',original_item_id='different-original-arm-id',scale=.75)
    raw=dict(**acquired,positions=list(range(8)),natural_site_l2=[10.]*8,composed_delta_l2=12.)
    if drift=='alias':raw['base_id']='other'
    if drift=='pointer_id':original['id']='other'
    if drift=='cohort':original['original_base_id']='other'
    if drift=='wrong_item_field':original['original_item_id']='0';original['original_base_id']='other'
    if drift=='dose':raw['alpha']=4
    if drift=='condition':raw['condition']='random'
    if drift=='scale':original['scale']=1.
    core.write(ptrdir/'ORIGINAL_POINTERS.PRIVATE.json',[original]);core.seal(ptrdir,'POINTER_SEAL.json',experiment='E135',input_sha256='wrong' if drift=='input_pin' else pin)
    core.write(native/'raw.json',[raw]);core.seal(native,'OUTPUT_SEAL.json',experiment='E135')
    sources=[dict(seal=str(p),sha256=core.sha(p)) for p in [native/'OUTPUT_SEAL.json',ptrdir/'POINTER_SEAL.json',acq/'INPUT_SEAL.json']]
    cell=rawcal()['cells'][0];cell['source_ref']=dict(seal_index=0,member='raw.json',keys=[0],field_mapping=dict(dose='alpha',condition='condition',write_positions='positions',natural_site_l2='natural_site_l2',composed_delta_l2='composed_delta_l2'),identity_mapping=dict(pointer_ref=dict(seal_index=1,member='ORIGINAL_POINTERS.PRIVATE.json',keys=[0]),acquisition_ref=dict(seal_index=2,member='items.json',keys=[0])))
    data=dict(cells=[cell]);meta=dict(source_seals=sources)
    import copy
    before=copy.deepcopy(data)
    if drift:
        with pytest.raises(ValueError):a.calibration_sources(data,meta)
    else:assert a.calibration_sources(data,meta)==data
    assert data==before
