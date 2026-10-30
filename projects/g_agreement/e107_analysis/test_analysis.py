import pytest
from . import rules as r
from . import adapter as a

def item(i,**systems):return dict(row='row',item_id=str(i),systems=systems)

def test_paired_conditional_denominators_are_per_output():
    xs=[item(0,oracle={'belief':1,'named':True},outside={'belief':0,'named':False}),item(1,oracle={'belief':0,'named':False},outside={'belief':0,'named':True}),item(2,oracle={'belief':1,'named':True},outside={'belief':0,'named':True})]
    z=r.compare(xs,'oracle','outside','belief',True)
    assert z['oracle']['estimate']==1 and z['outside']['estimate']==0
    assert z['counts']['oracle']['kept']==z['counts']['outside']['kept']==2
    assert z['counts']['oracle']['not_stating_value']==1

def test_item_pooled_not_equal_row_weight_and_paired_bootstrap():
    xs=[item(i,oracle={'belief':int(i==0),'named':True},outside={'belief':0,'named':True}) for i in range(4)]
    xs[0]['row']='small';z=r.compare(xs,'oracle','outside','belief',True)
    assert z['difference']['estimate']==.25
    for x in xs:x['systems']['outside']=dict(x['systems']['oracle'])
    assert r.compare(xs,'oracle','outside','belief',True)['difference']['CI95']==[0,0]

def test_unavailable_pairs_not_silently_compared_and_missing_not_zero():
    xs=[item(0,oracle={'belief':None,'named':None},outside={'belief':1,'named':True}),item(1,outside={'belief':0,'named':True})]
    z=r.compare(xs,'oracle','outside','belief',True)
    assert z['unmatched_source_items']==1 and z['oracle']['estimate'] is None
    assert z['outside']['estimate']==1 and z['counts']['oracle']['missing']==1

def test_rule_threshold_and_falsifier():
    assert r.verdict({'estimate':.2,'CI95':[.001,.4]})['R_OL1']=='MET'
    assert r.verdict({'estimate':.2,'CI95':[0,.4]})['R_OL1']=='NOT MET'
    assert r.verdict({'estimate':0,'CI95':[-.2,.2]})['falsifier']=='MET'
    assert r.verdict({'estimate':None,'CI95':None})['falsifier']=='NOT EVALUABLE'

def code(letter=None):return dict(id='synthetic',category='states_value' if letter else 'silent',values=[] if letter is None else [letter],evidence='' if letter is None else 'value')

def test_e82_dedicated_targets_both_and_missing_complete_pairs():
    meta=dict(id='x',bank='E82',cohort='belief_wrong',systems=['oracle'],target_letters={'belief':'A','truth':'B'})
    ms={'oracle':{'belief':dict(text='value',code=code('A'),target_letter='A'),'truth':dict(text='value',code=code('B'),target_letter='B')}}
    z=a.evaluate(meta,ms)['systems']['oracle'];assert z==dict(belief=1,truth=1,named=True)
    ms['oracle']['truth']['code']=None
    assert a.evaluate(meta,ms)['systems']['oracle']==dict(belief=None,truth=None,named=None)

def test_no_truth_never_invented_and_e81_signed_score():
    meta=dict(id='x',bank='E82',cohort='no_canonical_truth',systems=['outside'],target_letters={'belief':'A'})
    z=a.evaluate(meta,{'outside':{'belief':dict(text='value',code=code('A'),target_letter='A')}})
    assert 'truth' not in z['systems']['outside']
    meta.update(bank='E81',target_letters={'S':'B'})
    assert a.evaluate(meta,{'outside':{'S':dict(text='value',code=code('A'),target_letter='B')}})['systems']['outside']['S']==-1

def test_e86_unconditional_true_fact_rate_and_named_supplement():
    xs=[item(0,oracle={'truth':1,'named':True},outside={'truth':0,'named':False}),item(1,oracle={'truth':0,'named':False},outside={'truth':1,'named':True})]
    assert r.compare(xs,'oracle','outside','truth')['oracle']['estimate']==.5
    assert r.compare(xs,'oracle','outside','truth',True)['oracle']['estimate']==1

def test_report_oracle_confirmatory_exclusive_strict_no_new_ci_gate(monkeypatch):
    # Exact degenerate synthetic bootstrap accelerates report plumbing; shared
    # real5000-draw bootstrap is exercised by the paired tests above.
    def bootstrap(x,fn=None,**kw):
        import numpy as np
        p=float((fn or np.mean)(np.asarray(x)));return p,p,p
    monkeypatch.setattr(r,'bootstrap_ci',bootstrap)
    xs=[]
    for i in range(4):
        xs.append(dict(item(i,oracle={'belief':1,'named':True},nla={'belief':0,'named':True},outside={'belief':0,'named':True}),bank='E82',cohort='belief_wrong'))
        xs.append(dict(item(i,oracle={'truth':1,'named':True},nla={'truth':0,'named':False},outside={'truth':0,'named':True}),bank='E86'))
        xs.append(dict(item(i,oracle={'S':1},nla={'S':0},outside={'S':0},qwen_self={'S':0}),bank='E81'))
    z=r.analyze(xs,['row'])
    assert z['rules']['oracle']['R_OL1']=='MET' and z['rules']['nla_descriptive']['falsifier']=='MET'
    assert z['reader_exclusive']=={'oracle':['row'],'nla':[]}
    assert z['E86']['oracle']['pooled']['oracle']['estimate']==1

def test_source_gate_before_read(monkeypatch):
    monkeypatch.setattr(a,'committed',lambda:(_ for _ in ()).throw(ValueError('uncommitted')))
    monkeypatch.setattr(a,'read',lambda _:pytest.fail('output before source gate'))
    monkeypatch.setattr('sys.argv',['e107','--spec','never'])
    with pytest.raises(ValueError,match='uncommitted'):a.main()

def test_complete_sealed_bank_transport_and_tamper(tmp_path,monkeypatch):
    def bundle(name,files,**meta):
        p=tmp_path/name;p.mkdir()
        for k,v in files.items():a.write(p/k,v)
        a.core.seal(p,'SEAL.json',**meta)
        return p/'SEAL.json'
    e81rows=['r'+str(i) for i in range(37)];meta=[];measure=[]
    for bank,rows in [('E81',e81rows),('E82',['beliefrow']),('E86',['factrow'])]:
        for row in rows:
            systems=['oracle','nla','outside']+(['qwen_self'] if bank=='E81' else [])
            letters={'S':'A'} if bank=='E81' else {'belief':'A','truth':'B'} if bank=='E82' else {'truth':'A'}
            identity=bank+row;meta.append(dict(id=identity,bank=bank,row=row,item_id='same-colliding-id',systems=systems,target_letters=letters,cohort='belief_wrong'))
            measure.append(dict(id=identity,systems={system:{t:{field:dict(seal_index=0,member='raw.json',keys=['letters',bank,t] if field=='target_letter' else [field]) for field in ('text','code','target_letter')} for t in letters} for system in systems}))
    source=bundle('raw',{'raw.json':dict(text='value',code=code('A'),letters={'E81':{'S':'A'},'E82':{'belief':'A','truth':'B'},'E86':{'truth':'A'}})})
    inv=bundle('inventory',{'INVENTORY.json':meta},experiment='E107',e81_rows=e81rows,surviving_e82_rows=['beliefrow'],surviving_e86_rows=['factrow'])
    plan=bundle('plan',{'plans.json':[dict(inventory_id=x['id'],target='S') for x in meta[:5]]})
    audit=dict(redacted_records=5,affected=[dict(id=str(i),original_readout_sha256='a'*64,judge_readout_sha256='b'*64) for i in range(5)])
    mapping=dict(all_affected_mapped=True,plan_seal_sha256=a.sha(plan),plan_member_sha256=a.sha(plan.parent/'plans.json'),affected=[dict(opaque_id=str(i),inventory_id=meta[i]['id'],target='S',plan_index=i) for i in range(5)])
    privacy=bundle('privacy',{'audit.json':audit,'map.json':mapping})
    op=bundle('output',{'MEASUREMENTS.json':measure},experiment='E107',status='COMPLETE',inventory_sha256=a.sha(inv),route_verified=True,redaction_audit_complete=True,same_bank_rubrics=True,source_seals=[dict(seal=str(source),sha256=a.sha(source)),dict(seal=str(plan),sha256=a.sha(plan)),dict(seal=str(privacy),sha256=a.sha(privacy))],redaction_audit=dict(seal_index=2,member='audit.json',keys=[]),redaction_plan_map=dict(seal_index=2,member='map.json',keys=[]),redaction_original_plan=dict(seal_index=1,member='plans.json',keys=[]),outside_generation=dict(model='google/gemini-3.1-flash-lite',provider='google-vertex/global',temperature=0,max_tokens=256,ZDR=True,data_collection='deny',fallbacks=False))
    prior=bundle('prior',{'RESULTS.json':{}},status='COMPLETE_ONCE')
    monkeypatch.setattr(a,'ROOT',tmp_path);monkeypatch.setattr(a.subprocess,'check_output',lambda *args,**kw:inv.read_bytes())
    spec=dict(inventory_seal=str(inv),inventory_sha256=a.sha(inv),inventory_commit='a'*40,output_seal=str(op),output_sha256=a.sha(op),prior_analyses={bank:dict(seal=str(prior),sha256=a.sha(prior)) for bank in ('E82','E86')})
    rows,_,affected=a.inputs(spec);assert len(rows)==39 and len(affected)==5
    (source.parent/'raw.json').write_text('{}')
    with pytest.raises(ValueError,match='member mismatch'):a.inputs(spec)

def test_empty_naming_cohort_is_not_falsifier():
    xs=[item(i,oracle={'belief':0,'named':False},outside={'belief':0,'named':False}) for i in range(3)]
    z=r.compare(xs,'oracle','outside','belief',True)
    assert r.verdict(z['difference'])=={'R_OL1':'NOT EVALUABLE','falsifier':'NOT EVALUABLE'}


def test_opposite_original_reader_orders_same_semantic_answer():
    meta=dict(id='x',bank='E82',cohort='no_canonical_truth',systems=['oracle','nla','outside'],target_letters_by_system={'oracle':{'belief':'A'},'nla':{'belief':'B'},'outside':{'belief':'B'}})
    ms={system:{'belief':dict(text='value',code=code(letter),target_letter=letter)} for system,letter in [('oracle','A'),('nla','B'),('outside','B')]}
    z=a.evaluate(meta,ms)['systems']
    assert all(x==dict(belief=1,named=True) for x in z.values())
    # Global legacy mapping is safe only when every original sealed map agrees.
    del meta['target_letters_by_system'];meta['target_letters']={'belief':'A'}
    with pytest.raises(ValueError,match='original sealed'):a.evaluate(meta,ms)

def test_legacy_identical_mapping_requires_sealed_letter_for_every_target():
    meta=dict(id='x',bank='E82',cohort='no_canonical_truth',systems=['oracle','nla'],target_letters={'belief':'B'})
    ms={s:{'belief':dict(text='value',code=code('B'),target_letter='B')} for s in meta['systems']}
    assert a.evaluate(meta,ms)['systems']['nla']['belief']==1
    del ms['nla']['belief']['target_letter']
    with pytest.raises(KeyError):a.evaluate(meta,ms)


def test_e49_unavailable_native_codes_preserve_all_baselines_and_unknown_membership(monkeypatch):
    import numpy as np
    monkeypatch.setattr(r,'bootstrap_ci',lambda v,fn=None,**kw:(lambda p:(p,p,p))((fn or np.mean)(np.asarray(v))))
    names=['e49_'+str(i) for i in range(14)]+['other_'+str(i) for i in range(23)]
    xs=[]
    for name in names:
        for i in range(84):
            systems=dict(outside={'S':1},qwen_self={'S':-1})
            if not name.startswith('e49_'):systems.update(oracle={'S':1},nla={'S':0})
            xs.append(dict(bank='E81',row=name,item_id=str(i),systems=systems))
    z=r.analyze(xs,names)
    assert len(z['E81'])==len(z['E81_baseline_comparison'])==37
    for name in names:
        assert z['E81_baseline_comparison'][name]['difference']['estimate']==2
        assert z['E81_baseline_comparison'][name]['counts']['outside']['kept']==84
    for name in names[:14]:
        for reader in ('oracle','nla'):
            v=z['E81'][name][reader]
            assert v['reader_exclusive'] is None and v['unavailable_native_code_items']==84
            assert v['three_way_items']==0 and name not in z['reader_exclusive'][reader]
