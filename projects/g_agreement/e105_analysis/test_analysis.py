import pytest
from . import rules as r
from . import adapter as a

def records():
    return [dict(id=f'{row}:{i}',item_id=str(i),row=row,contrasts={'0':-1.,'S':-1.,'T':1.}) for row in r.ROWS for i in range(84)]

def test_gate_bt1_and_paired_delta():
    z=r.analyze(records());assert z['rules']['positive_control_gate']['status']=='MET'
    assert z['rules']['R-BT1']['status']=='MET' and z['rules']['falsifier']['status']=='NOT MET'
    x=z['rows']['nesting_depth'];assert x['delta']['CI95']==[2.,2.] and x['flip_T']['estimate']==1 and x['flip_S']['estimate']==0

def test_gate_failure_forces_not_evaluable():
    xs=records()
    for x in xs:
        if x['row'] in r.POSITIVE:x['contrasts']['T']=-1.
    z=r.analyze(xs);assert z['rules']['positive_control_gate']['status']=='NOT MET'
    assert z['rules']['R-BT1']['status']=='NOT EVALUABLE'

def test_flip_difference_is_required_despite_positive_delta():
    xs=records()
    for x in xs:
        if x['row'] in r.MISSED:x['contrasts'].update(T=-.1,S=-1.)
    z=r.analyze(xs);assert z['rules']['R-BT1']['status']=='NOT MET'
    assert z['rows']['nesting_depth']['delta']['estimate']>0

def test_falsifier_all_three_and_non_strict_zero_lower():
    xs=records()
    for x in xs:
        if x['row'] in r.MISSED:x['contrasts']['T']=-1.
    assert r.analyze(xs)['rules']['falsifier']['status']=='MET'
    for x in xs:
        if x['row']=='indent_level':x['contrasts']['T']=1.
    assert r.analyze(xs)['rules']['falsifier']['status']=='NOT MET'

def test_baseline_relative_reversal_both_directions_and_ties():
    xs=records()
    for x in xs:
        i=int(x['item_id'])
        if i<28:x['contrasts'].update({'0':1.,'T':-1.,'S':1.})
        elif i<56:x['contrasts'].update({'0':0.,'T':1.,'S':-1.})
        else:x['contrasts'].update({'0':-1.,'T':0.,'S':0.})
    z=r.analyze(xs)['rows']['fact_recall'];assert z['flip_T']['estimate']==pytest.approx(1/3)
    assert z['flip_S']['estimate']==0 and z['baseline_ties']==28 and z['T_ties']==28

def test_thresholds_no_added_flip_ci_gate():
    stats={row:dict(delta={'estimate':.1,'CI95':[.01,.2]},flip_difference={'estimate':.2,'CI95':[-.5,.5]}) for row in r.ROWS}
    assert r.evaluate(stats)['R-BT1']['status']=='MET'
    stats['format_plan']['delta']['CI95'][0]=0;stats['language_plan']['delta']['CI95'][0]=0
    assert r.evaluate(stats)['R-BT1']['status']=='NOT EVALUABLE'

def raw_fixture():
    xs=[];targets={}
    for row in r.ROWS:
        for i in range(84):
            own=i%2;donor=1-own;ident=f'{row}:{i}';td=f'{row}:{(i+1)%84}';sd=f'{row}:{(i+2)%84}'
            targets[ident]=dict(row=row,donor_id=td,target='A' if donor else 'B')
            sign=1 if donor else -1
            xs.append(dict(id=ident,item_id=ident,row=row,split='test',T_donor_id=td,S_donor_id=sd,source_label=own,T_label=donor,S_label=own,candidate_A_label=1,frozen_scorer_sha256='synthetic',candidate_ids_sha256='synthetic',candidate_pair_count=2,pair_logprobs={'T':[[sign,0],[3*sign,0]],'S':[[-sign,0],[-sign,0]],'0':[[-sign,0],[-sign,0]]}))
    return xs,targets

def test_fixed_T_orientation_full_pairs_no_S_sign_switch():
    xs,t=raw_fixture();z=a.normalize(xs,t)
    assert len(z)==504 and all(x['contrasts']=={'T':2.,'S':-1.,'0':-1.} for x in z)
    assert r.analyze(z)['rows']['page_range_digit']['delta']['estimate']==3

def test_custody_rejects_wrong_pairing_labels_missing_and_nonfinite():
    for change in ('T_donor_id','S_label','missing','nonfinite'):
        xs,t=raw_fixture()
        if change=='T_donor_id':xs[0][change]=xs[0]['item_id']
        elif change=='S_label':xs[0][change]=1-xs[0][change]
        elif change=='missing':xs.pop()
        else:xs[0]['pair_logprobs']['T'][0][0]=float('nan')
        with pytest.raises(ValueError):a.normalize(xs,t)

def test_shared_bootstrap_reproducible_and_finite_guard():
    assert r.statistic([1,2,3])==r.statistic([1,2,3])
    with pytest.raises(ValueError):r.statistic([1,float('nan')])

def test_source_gate_before_output(monkeypatch):
    monkeypatch.setattr(a,'committed',lambda:(_ for _ in ()).throw(ValueError('uncommitted')))
    monkeypatch.setattr(a,'read',lambda _:pytest.fail('read before commit'))
    monkeypatch.setattr('sys.argv',['e105','--spec','never'])
    with pytest.raises(ValueError,match='uncommitted'):a.main()

def test_sealed_1512_condition_transport_and_tamper(tmp_path,monkeypatch):
    xs,targets=raw_fixture()
    def bundle(name,files,**meta):
        p=tmp_path/name;p.mkdir()
        for k,v in files.items():a.write(p/k,v)
        a.core.seal(p,'SEAL.json',**meta)
        return p/'SEAL.json'
    tp=bundle('targets',{'TARGETS.json':[dict(v,id=k) for k,v in targets.items()]})
    monkeypatch.setattr(a,'E100_TARGET_SHA',a.sha(tp))
    raw=[x.pop('pair_logprobs') for x in xs]
    source=bundle('raw',{'raw.json':raw},status='COMPLETE')
    inv=bundle('inventory',{'INVENTORY.json':xs},experiment='E105',same_value_seed=20261030,block=44,supplied_vector_mode=True,behaviour_mode='frozen_continuation',new_text=False)
    measurements=[dict(id=x['id'],conditions={c:dict(seal_index=0,member='raw.json',keys=[i,c]) for c in ('T','S','0')}) for i,x in enumerate(xs)]
    op=bundle('output',{'MEASUREMENTS.json':measurements},experiment='E105',status='COMPLETE',inventory_sha256=a.sha(inv),source_seals=[dict(seal=str(source),sha256=a.sha(source))],restart_resolution=dict(status='E105_RESTART_RESOLVED',authority='§214 amendment2 / 157fb545',rows={row:dict(status='COMPLETE',source_seal_index=0) for row in r.ROWS}))
    monkeypatch.setattr(a,'ROOT',tmp_path)
    monkeypatch.setattr(a.subprocess,'check_output',lambda *args,**kw:inv.read_bytes())
    spec=dict(inventory_seal=str(inv),inventory_commit='a'*40,inventory_sha256=a.sha(inv),e100_targets=str(tp),output_seal=str(op),output_sha256=a.sha(op))
    assert len(a.inputs(spec))==504
    (source.parent/'raw.json').write_text('[]')
    with pytest.raises(ValueError,match='member mismatch'):a.inputs(spec)


def test_amendment2_two_missed_need_both_and_two_controls_need_both():
    complete=set(r.ROWS)-{'indent_level','fact_recall'}
    xs=[x for x in records() if x['row'] in complete]
    z=r.analyze(xs,complete)
    assert z['rules']['R-BT1']['status']=='MET' and z['rules']['R-BT1']['required']==2
    for x in xs:
        if x['row']=='nesting_depth':x['contrasts']['T']=-1
    assert r.analyze(xs,complete)['rules']['R-BT1']['status']=='NOT MET'
    for x in xs:
        if x['row']=='format_plan':x['contrasts']['T']=-1
    assert r.analyze(xs,complete)['rules']['R-BT1']['status']=='NOT EVALUABLE'

def test_amendment2_falsifier_retains_all3_and_missing_is_unknown():
    complete=set(r.ROWS)-{'indent_level','fact_recall'};xs=[x for x in records() if x['row'] in complete]
    for x in xs:
        if x['row'] in r.MISSED:x['contrasts']['T']=-1
    z=r.analyze(xs,complete)
    assert z['rules']['falsifier']['status']=='NOT EVALUABLE' and z['rules']['falsifier']['required']==3
    assert set(z['not_run_operational'])=={'indent_level','fact_recall'}
    assert 'indent_level' not in z['rows']

def test_amendment2_no_other_omission_or_partial_row():
    with pytest.raises(ValueError):r.analyze([x for x in records() if x['row']!='format_plan'],set(r.ROWS)-{'format_plan'})
    xs,t=raw_fixture();complete=set(r.ROWS)-{'indent_level'};xs=[x for x in xs if x['row'] in complete]
    assert len(a.normalize(xs,t,complete))==420
    with pytest.raises(ValueError):a.normalize(xs[:-1],t,complete)

def test_amendment2_terminal_resolution_required_and_failures_sealed():
    rows={x:dict(status='COMPLETE',source_seal_index=0) for x in r.ROWS}
    s=dict(restart_resolution=dict(status='E105_RESTART_RESOLVED',authority='§214 amendment2 / 157fb545',rows=rows))
    sources=[dict(status='COMPLETE'),dict(status='NO_FIT'),dict(status='NO_FIT')]
    rows['indent_level']=dict(status='NOT RUN (operational)',attempt_seal_indices=[1,2])
    assert set(a.resolved_rows(s,sources))==set(r.ROWS)-{'indent_level'}
    rows['indent_level']['attempt_seal_indices']=[1]
    with pytest.raises(ValueError,match='restart'):a.resolved_rows(s,sources)
    s['restart_resolution']['status']='PENDING'
    with pytest.raises(ValueError,match='resolution'):a.resolved_rows(s,sources)
