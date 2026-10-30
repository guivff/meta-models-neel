from pathlib import Path
import pytest
from . import adapter as a,screen,rules


def fixture(tmp,monkeypatch):
    monkeypatch.setattr(a,'GUARD',tmp/'canonical'/'ANALYSIS_ONCE.json');monkeypatch.setattr(a,'protocol',lambda:None)
    pairs=[];grid=[];raw=[]
    def ptr(index,key):return dict(seal_index=0,member='original.json',keys=[index,key])
    for i,kind in enumerate(['multi_hop','multi_hop','one_hop']):
        p=dict(pair_id=str(i),generation_index=i,kind=kind,pair_count=1,recipient_pair_indices=[0],recipient_contrast_sha256='original-recipient-token-pair',value_map={'A':'Erin','B':'Dana','C':'Carl'},members=[])
        mm=[]
        for j,current in enumerate(['Erin','Carl']):
            label=dict(member=j,item_id=f'{i}:{j}',current=current,previous='Dana',current_previous_contrast_sha256='original-native-pair',current_in_preference='A',current_previous_pair_indices=[0]);p['members'].append(label)
            def cell(mode,block=None,control=None):
                index=len(raw);rid=f'{i}:{j}:{mode}:{block}:{control}'
                identity=dict(pair_id=str(i),kind=kind,item_id=label['item_id'],member=j,mode=mode,block=block,control=control,raw_id=rid,contrast_sha256=p['recipient_contrast_sha256'],pair_count=1,current_previous_contrast_sha256=label['current_previous_contrast_sha256'],judgment_id=rid,donor_pair_id=str(i),donor_member=1-j,patch_binding_verified=True,unscaled_residual_replacement=True,position=0 if control=='earlier_token'else 20,read_index=20,norm_matched=True,random_seed=20261030)
                value=(-1 if j==0 else 1)if mode=='own'else 0
                record=dict(id=rid,text=current,token_ids=[1],greedy_max_new_tokens=32,pair_logits=[[2,1]],pair_logprobs=[[-4+value,-4]],first_token_logprobs=[[-2,-3]],probability_kind='global_vocab_logsoftmax_at_read',candidate_first_token_ids=[[1,2]])
                raw.append(dict(identity=identity,raw=record,record=record,text='Erin Dana Carl',code=dict(id=rid,category='states_value',values=['B']if block==44 else['A'if j==0 else'C'],evidence='Erin Dana Carl'),vector=[float(i),float(j)]))
                return dict(identity=ptr(index,'identity'),raw=ptr(index,'raw'),record=ptr(index,'record'),code=ptr(index,'code'),text=ptr(index,'text'),vector=ptr(index,'vector'))
            mm.append(dict(greedy=cell('greedy'),preference=cell('preference'),own=cell('own'),readouts={str(l):cell('readout',l)for l in rules.READS},vectors={str(l):cell('vector',l)for l in a.probes.LAYERS},patches={str(b):{c:cell('patch',b,c)for c in rules.PATCHES}for b in (rules.BLOCKS if kind=='multi_hop'else(44,52))}))
        pairs.append(p);grid.append(dict(pair_id=str(i),members=mm))
    def bundle(name,files,**meta):
        d=tmp/name;d.mkdir()
        for n,v in files.items():a.core.write(d/n,v)
        a.core.seal(d,'SEAL.json',**meta);return d/'SEAL.json'
    proof=dict(classifier_sha256=screen.MATCHER_SHA256,selected={'multi_hop':['0','1'],'one_hop':['2']},screening=[dict(pair_id=p['pair_id'],kind=p['kind'],generation_index=p['generation_index'],correct_both=True)for p in pairs])
    for j in range(298):proof['screening'].append(dict(pair_id=f'multi-failed:{j}',kind='multi_hop',generation_index=3+j,correct_both=False))
    for j in range(149):proof['screening'].append(dict(pair_id=f'one-failed:{j}',kind='one_hop',generation_index=301+j,correct_both=False))
    sp=bundle('screen',{'SCREEN_SELECTION.PRIVATE.json':proof},experiment='E133',status='COMPLETE_ONCE')
    ip=bundle('inventory',{'PAIRS.PRIVATE.json':pairs,'FIXED_NAMES.PRIVATE.json':['Erin','Dana','Carl','Evan']},experiment='E133',status='SCREENED_COHORT_FROZEN',labels_cpu_only=True,classifier_sha256=screen.MATCHER_SHA256,greedy_max_new_tokens=32,screen_seal=str(sp),screen_sha256=a.core.sha(sp))
    source=bundle('source',{'original.json':raw},experiment='E133',status='COMPLETE')
    op=bundle('output',{'MEASUREMENTS.json':grid},experiment='E133',status='COMPLETE',inventory_sha256=a.core.sha(ip),reader_layers=[44,52,60],vector_layers=list(a.probes.LAYERS),no_steer=True,judging_bank='E133',judging_cap_usd=4,route_verified=True,redaction_audit_complete=True,labels_cpu_only=True,rubric_sha256='frozen-C-adapted-rubric',source_seals=[dict(seal=str(source),sha256=a.core.sha(source))])
    return dict(inventory_seal=str(ip),inventory_sha256=a.core.sha(ip),output_seal=str(op),output_sha256=a.core.sha(op),native_output_sha256=a.core.sha(source),rubric_sha256='frozen-C-adapted-rubric',analysis=str(tmp/'analysis')),source


def reseal(spec,source,change):
    rows=a.core.read(source.parent/'original.json');change(rows);a.core.write(source.parent/'original.json',rows)
    meta=a.core.read(source);meta.pop('files');a.core.seal(source.parent,source.name,**meta)
    op=Path(spec['output_seal']);meta=a.core.read(op);meta.pop('files');meta['source_seals'][0]['sha256']=a.core.sha(source);a.core.seal(op.parent,op.name,**meta);spec['output_sha256']=a.core.sha(op);spec['native_output_sha256']=a.core.sha(source)


def test_full_sealed_binding_one_run_local_audit_and_no_replay(tmp_path,monkeypatch):
    spec,_=fixture(tmp_path,monkeypatch);s=a.run(spec,'synthetic-only');r=a.core.read(s.parent/'RESULTS.json')
    assert r['R_NL1']=='DESCRIPTIVE ONLY'and r['groups']['multi_hop']['n_pairs']==2
    assert r['groups']['multi_hop']['reader_rates']['44']['previous']['estimate']==1
    assert 'text_preference_agreement'not in r['text_preference_descriptive']['multi_hop']
    assert (s.parent/'PER_PAIR.PRIVATE.json').stat().st_mode&0o777==0o600
    with pytest.raises(ValueError,match='once guard'):a.run(spec,'synthetic-only')


def test_changed_source_contrast_fails_closed_and_retains_claim(tmp_path,monkeypatch):
    spec,source=fixture(tmp_path,monkeypatch)
    def corrupt(rows):next(r for r in rows if r['identity']['mode']=='patch')['identity']['contrast_sha256']='different'
    reseal(spec,source,corrupt)
    with pytest.raises(ValueError,match='ordered recipient contrast'):a.run(spec,'synthetic')
    assert a.GUARD.exists() # failure is never a free re-run


@pytest.mark.parametrize('field,bad',[('judging_cap_usd',5.01),('no_steer',False),('route_verified',False)])
def test_wrong_registered_settings_not_silently_admitted(tmp_path,monkeypatch,field,bad):
    spec,_=fixture(tmp_path,monkeypatch);p=Path(spec['output_seal']);m=a.core.read(p);m.pop('files');m[field]=bad;a.core.seal(p.parent,p.name,**m);spec['output_sha256']=a.core.sha(p)
    with pytest.raises(ValueError):a.run(spec,'synthetic')


def test_null_is_missing_only_with_original_same_id_terminal(tmp_path,monkeypatch):
    spec,source=fixture(tmp_path,monkeypatch)
    def missing(rows):
        r=next(r for r in rows if r['identity']['mode']=='readout');r.update(id=r['identity']['judgment_id'],status='UNPARSEABLE',code=None)
    reseal(spec,source,missing);s=a.run(spec,'synthetic');r=a.core.read(s.parent/'RESULTS.json')
    assert r['groups']['multi_hop']['reader_rates']['44']['previous']['missing_n']==1


def test_cli_commit_and_protocol_gate_before_spec_io(monkeypatch):
    import sys
    monkeypatch.setattr(sys,'argv',['adapter','--spec','not-opened'])
    def fail():raise ValueError('protocol pending')
    monkeypatch.setattr(a,'committed',fail);monkeypatch.setattr(a.core,'read',lambda _:pytest.fail('source opened before committed protocol'))
    with pytest.raises(ValueError,match='pending'):a.main()


def test_pending_protocol_blocks_imported_run_before_metadata_or_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(a,'GUARD',tmp_path/'guard.json')
    monkeypatch.setattr(a.core,'read',lambda _:dict(status='CLARIFICATION_PENDING'))
    monkeypatch.setattr(a,'metadata',lambda _:pytest.fail('outcome/spec opened while protocol pending'))
    with pytest.raises(ValueError,match='clarification pending'):a.run({},'synthetic')
    assert not a.GUARD.exists()


def test_missing_descriptive_probability_mass_is_reported_not_renormalized(tmp_path,monkeypatch):
    spec,source=fixture(tmp_path,monkeypatch)
    def remove(rows):
        for row in rows:
            if row['identity']['mode']=='preference':
                row['record'].pop('first_token_logprobs');row['record'].pop('candidate_first_token_ids')
    reseal(spec,source,remove);s=a.run(spec,'synthetic');r=a.core.read(s.parent/'RESULTS.json')
    z=r['text_preference_descriptive']['multi_hop']
    assert z['candidate_mass_missing_n']==4 and z['candidate_mass_quartiles']is None
    assert z['preferred_is_greedy_first']['missing_n']==4


def test_original_indexed_common_recipient_pair_never_averages_other_contrasts(tmp_path,monkeypatch):
    spec,source=fixture(tmp_path,monkeypatch)
    def unrelated(rows):
        for row in rows:
            if row['identity']['mode']in ('own','patch'):
                row['raw']['pair_logprobs'].append([-1000.,-1.])
    reseal(spec,source,unrelated);s=a.run(spec,'synthetic');r=a.core.read(s.parent/'RESULTS.json')
    assert r['groups']['multi_hop']['patches']['44']['read_token']['estimate']==.5


def test_first_opening_receipt_before_outcome_join(tmp_path,monkeypatch):
    spec,_=fixture(tmp_path,monkeypatch);original=a.inputs
    def checked(spec,inventory):
        record=a.core.read(Path(spec['analysis'])/'FIRST_OPENING.json')
        assert record['output_sha256']==spec['output_sha256']and record['utc']
        return original(spec,inventory)
    monkeypatch.setattr(a,'inputs',checked)
    s=a.run(spec,'synthetic');assert 'FIRST_OPENING.json'in a.core.read(s)['files']


def test_rq_two_contrast_reproducer_registered_R_half_not_mixed_one_twelfth(tmp_path,monkeypatch):
    """daa20e078: own common=-2/other=+2/patch=0; extra contrast=0/20/0."""
    from copy import deepcopy
    spec,source=fixture(tmp_path,monkeypatch)
    def native_shape(rows):
        for row in rows:
            ident=row['identity'];j=ident['member'];mode=ident['mode']
            if mode=='own':row['raw']['pair_logprobs']=[[-4.,-2.],[-4.,-4.]]if j==0 else[[-2.,-4.],[-1.,-21.]]
            elif mode=='patch':row['raw']['pair_logprobs']=[[-3.,-3.],[-4.,-4.]]
            elif mode=='preference':
                row['record']['pair_logits']=[[100.,0.],[-1.,0.]]if j==0 else[[-100.,0.],[1.,0.]]
                row['record']['first_token_logprobs']=[[-.1,-100.1],[-2.,-1.]]if j==0 else[[-100.1,-.1],[-1.,-2.]]
                row['record']['candidate_first_token_ids']=[[1,2],[3,4]]
    reseal(spec,source,native_shape)
    ip=Path(spec['inventory_seal']);inv=a.core.read(ip.parent/'PAIRS.PRIVATE.json')
    for p in inv:
        assert p['recipient_pair_indices']==[0]
        for m in p['members']:m['current_previous_pair_indices']=[1]
    a.core.write(ip.parent/'PAIRS.PRIVATE.json',inv);meta=a.core.read(ip);meta.pop('files');a.core.seal(ip.parent,ip.name,**meta);spec['inventory_sha256']=a.core.sha(ip)
    op=Path(spec['output_seal']);meta=a.core.read(op);meta.pop('files');meta['inventory_sha256']=spec['inventory_sha256'];a.core.seal(op.parent,op.name,**meta);spec['output_sha256']=a.core.sha(op)
    raw_before=deepcopy(a.core.read(source.parent/'original.json'))
    data=a.inputs(spec,a.metadata(spec)['pairs'])
    for pair in data:
        assert [m['own_logodds']for m in pair['members']]==[-2.,2.]
        # Separate current/previous preference must defeat the opposite common-pair sign.
        assert [m['preference_current']for m in pair['members']]==[False,True]
        for m in pair['members']:
            assert all(v==0 for block in m['patches'].values()for v in block.values())
    s=a.run(spec,'synthetic-rq-reproducer');r=a.core.read(s.parent/'RESULTS.json')
    for block in ('44','48','52','56','60'):
        for control in rules.PATCHES:
            assert r['groups']['multi_hop']['patches'][block][control]['estimate']==.5
            assert r['groups']['multi_hop']['patches'][block][control]['CI95']==[.5,.5]
    mixed_R=(0-(-2+0)/2)/((2+20)/2-(-2+0)/2)
    assert mixed_R==pytest.approx(.08333333333333333) # the OLD invalid calculation
    assert a.core.read(source.parent/'original.json')==raw_before


def test_original_pair_row_selection_keeps_source_order_and_rows():
    values=[[-4.,-2.],[-1.,-21.]]
    selected=a.original_pairs(values,[0])
    assert selected==[[-4.,-2.]]and selected[0]is values[0]
    for indices in [[],[0,0],[2],[-1],[True]]:
        with pytest.raises(ValueError):a.original_pairs(values,indices)


def test_truth_off_unordered_candidates_use_cpu_indices_not_first_second_assumption(tmp_path,monkeypatch):
    spec,source=fixture(tmp_path,monkeypatch)
    def native_unordered(rows):
        for row in rows:
            mode=row['identity']['mode']
            if mode in ('own','patch'):row['raw']['pair_logprobs'].insert(0,[-1000.,-1.])
            elif mode=='preference':
                row['record']['pair_logits'].insert(0,[-100.,0.])
                row['record']['first_token_logprobs'].insert(0,[-100.1,-.1])
                row['record']['candidate_first_token_ids'].insert(0,[9,8])
    reseal(spec,source,native_unordered)
    ip=Path(spec['inventory_seal']);inv=a.core.read(ip.parent/'PAIRS.PRIVATE.json')
    for p in inv:
        p['recipient_pair_indices']=[1]
        for m in p['members']:m['current_previous_pair_indices']=[1]
    a.core.write(ip.parent/'PAIRS.PRIVATE.json',inv);meta=a.core.read(ip);meta.pop('files');a.core.seal(ip.parent,ip.name,**meta);spec['inventory_sha256']=a.core.sha(ip)
    op=Path(spec['output_seal']);meta=a.core.read(op);meta.pop('files');meta['inventory_sha256']=spec['inventory_sha256'];a.core.seal(op.parent,op.name,**meta);spec['output_sha256']=a.core.sha(op)
    s=a.run(spec,'synthetic-unordered-candidates');r=a.core.read(s.parent/'RESULTS.json')
    assert r['groups']['multi_hop']['patches']['44']['read_token']['estimate']==.5
    assert 'text_preference_agreement'not in r['text_preference_descriptive']['multi_hop']


def without_preference(spec):
    op=Path(spec['output_seal']);grid=a.core.read(op.parent/'MEASUREMENTS.json')
    for pair in grid:
        for member in pair['members']:member.pop('preference')
    a.core.write(op.parent/'MEASUREMENTS.json',grid);meta=a.core.read(op);meta.pop('files');a.core.seal(op.parent,op.name,**meta);spec['output_sha256']=a.core.sha(op)


def test_deviation1_absent_unmeasured_preference_preserves_rnl1(tmp_path,monkeypatch):
    spec,_=fixture(tmp_path,monkeypatch)
    import json
    before=a.inputs(spec,a.metadata(spec)['pairs']);expected=json.loads(json.dumps(rules.analyze(before)[0]))
    without_preference(spec)
    # Actual frozen inventory has no current-vs-previous contrast metadata either.
    ip=Path(spec['inventory_seal']);pairs=a.core.read(ip.parent/'PAIRS.PRIVATE.json')
    for p in pairs:
        for m in p['members']:
            for key in ['current_previous_contrast_sha256','current_previous_pair_indices','current_in_preference']:m.pop(key)
    a.core.write(ip.parent/'PAIRS.PRIVATE.json',pairs);meta=a.core.read(ip);meta.pop('files');a.core.seal(ip.parent,ip.name,**meta);spec['inventory_sha256']=a.core.sha(ip)
    op=Path(spec['output_seal']);meta=a.core.read(op);meta.pop('files');meta['inventory_sha256']=spec['inventory_sha256'];a.core.seal(op.parent,op.name,**meta);spec['output_sha256']=a.core.sha(op)
    seal=a.run(spec,'synthetic-deviation1');result=a.core.read(seal.parent/'RESULTS.json')
    assert result['groups']==expected['groups']and result['R_NL1']==expected['R_NL1']and result['falsifier']==expected['falsifier']
    for z in result['text_preference_descriptive'].values():
        assert z['preference_status']=='NOT MEASURED'and 'text_preference_agreement'not in z
        assert z['candidate_mass_quartiles']is None


@pytest.mark.parametrize('field',['greedy','own','readouts','vectors','patches'])
def test_deviation1_only_preference_is_optional_other_missing_fields_fail_closed(tmp_path,monkeypatch,field):
    spec,_=fixture(tmp_path,monkeypatch);without_preference(spec)
    op=Path(spec['output_seal']);grid=a.core.read(op.parent/'MEASUREMENTS.json');grid[0]['members'][0].pop(field)
    a.core.write(op.parent/'MEASUREMENTS.json',grid);meta=a.core.read(op);meta.pop('files');a.core.seal(op.parent,op.name,**meta);spec['output_sha256']=a.core.sha(op)
    with pytest.raises(ValueError,match='only preference may be absent'):a.run(spec,'synthetic-missing-required')
    assert a.GUARD.exists() # never reset a failed claim


def test_deviation1_original_capture_flag_false_never_infers_recipient_preference(tmp_path,monkeypatch):
    spec,source=fixture(tmp_path,monkeypatch)
    def original(rows):
        for r in rows:
            if r['identity']['mode']=='preference':r['identity']['current_previous_contrast_captured']=False
    reseal(spec,source,original)
    data=a.inputs(spec,a.metadata(spec)['pairs'])
    assert all(m['preference_status']=='NOT MEASURED'and m['preference_current']is None and m['first_token_candidate_probability_masses']is None for p in data for m in p['members'])
    assert all(z['preference_status']=='NOT MEASURED'and 'text_preference_agreement'not in z for z in a.descriptives(data).values())


def test_deviation1_invalid_capture_flag_fails_closed(tmp_path,monkeypatch):
    spec,source=fixture(tmp_path,monkeypatch)
    def invalid(rows):
        for r in rows:
            if r['identity']['mode']=='preference':r['identity']['current_previous_contrast_captured']='false'
    reseal(spec,source,invalid)
    with pytest.raises(ValueError,match='captured-preference boolean'):a.run(spec,'synthetic-invalid-flag')
