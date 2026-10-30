import pytest
from . import rules as r,adapter as a

def code(i,values):return dict(id=i,category='states_value' if values else 'silent',values=values,evidence='value' if values else '')
def row(i,values):return a.evaluate(dict(id=str(i),reader='oracle',arm='role'),code(str(i),values),'value')

def test_conditional_denominator_both_neither_missing():
    xs=[row(0,['A']),row(1,['B']),row(2,['A','B']),row(3,[]),a.evaluate(dict(id='4',reader='oracle',arm='role'),None,'')]
    z=r.summary(xs)
    assert z['planned']==5 and z['kept']==4 and z['missing']==1 and z['naming_either_value']==3
    assert z['both']==1 and z['neither']==1 and z['conditional_wrong_minus_truth']['estimate']==0
    assert z['conditional_truth']['estimate']==pytest.approx(2/3) and z['unconditional_truth']['estimate']==.5

def test_truth_first_direction_and_evidence_identity():
    assert row(0,['A'])['truth_score']==1 and row(1,['B'])['truth_score']==-1
    with pytest.raises(ValueError,match='identity'):a.evaluate(dict(id='x'),code('y',['A']),'value')
    with pytest.raises(ValueError,match='evidence'):a.evaluate(dict(id='x'),code('x',['A']),'wrong span')

def test_named_item_bootstrap_reproducible():
    xs=[row(i,['A'] if i%3==0 else ['B']) for i in range(84)]
    first=r.summary(xs);assert first==r.summary(xs[::-1])
    assert first==r.summary(xs)
    lo,hi=first['conditional_wrong_minus_truth']['CI95'];assert lo<first['conditional_wrong_minus_truth']['estimate']<hi

def test_all_missing_and_no_named_are_not_zero():
    assert r.summary([a.evaluate(dict(id='x'),None,'')])['conditional_wrong_minus_truth']['estimate'] is None
    assert r.summary([row(0,[])])['conditional_truth']['estimate'] is None
    assert r.summary([row(0,[])])['unconditional_truth']['estimate']==0

def test_rk1_never_inferred_from_binary_role_and_old_subset():
    xs=[row(i,['B']) for i in range(8)];old=[row(0,['A']),row(1,['A'])]
    z=r.analyze(xs,old,{'0','1'},{})
    assert z['R_K1']==z['falsifier']=='NOT EVALUABLE'
    assert z['R_K2_descriptive']['oracle']['role']['conditional_wrong_minus_truth']['estimate']==1
    assert z['matched_original_rubric']['primary']['oracle']['role']['planned']==2
    assert z['matched_original_rubric']['original']['oracle']['role']['conditional_wrong_minus_truth']['estimate']==-1

def test_original_sample_fixed_independent_of_order():
    ids=[str(i) for i in range(800)];assert len(a.original_ids(ids))==200
    assert a.original_ids(ids)==a.original_ids(ids[::-1])

def test_commit_gate_before_io(monkeypatch):
    monkeypatch.setattr(a,'committed',lambda:(_ for _ in ()).throw(ValueError('uncommitted')))
    monkeypatch.setattr(a,'read',lambda _:pytest.fail('output read before commit gate'))
    monkeypatch.setattr('sys.argv',['e86','--spec','never'])
    with pytest.raises(ValueError,match='uncommitted'):a.main()

def test_full_original_grid_transport_and_tamper(tmp_path,monkeypatch):
    def bundle(name,files,**meta):
        p=tmp_path/name;p.mkdir()
        for k,v in files.items():a.write(p/k,v)
        a.core.seal(p,'SEAL.json',**meta);return p/'SEAL.json'
    meta=[dict(id=f'{reader}:{arm}:{i}',reader=reader,arm=arm,source_id=str(i),capture_public_id=f'{arm}:{i}',subset='yn',split='test',correct_value='A') for reader in ('oracle','nla') for arm in ('honest','role') for i in range(200)]
    private=tmp_path/'private.json';a.write(private,meta);wanted=a.original_ids([x['id'] for x in meta])
    counts={subset+'/'+arm:dict(dev=200,test=200,released_test=200 if subset=='yn' and arm in ('honest','role') else 0) for subset in ('open','yn') for arm in ('honest','lie','role')}
    probes={arm+'/'+str(layer):dict(status='COMPLETE',dev_auroc=.99,test_auroc=.99) for arm in ('honest','lie','role') for layer in (42,44)}
    raw=bundle('science',{'raw.json':dict(text='value',codes={x['id']:code(x['id'],['A']) for x in meta},achieved_counts=counts,truth_probes=probes)})
    release=tmp_path/'release.json';a.write(release,dict(released_ids=sorted({x['capture_public_id'] for x in meta})))
    packet=bundle('packet',{'packet.json':{}},scientific_output_seal_sha256=a.sha(raw),release_sha256=a.sha(release),complete=True,behaviour_gate_verified=True,value_order='truth_then_lie')
    pre=tmp_path/'PREFLIGHT.json';a.write(pre,dict(private_join_sha256=a.sha(private),source_seal_sha256=a.sha(packet)))
    monkeypatch.setattr(a,'PREFLIGHT',pre);monkeypatch.setattr(a,'SCIENCE_DIGEST',a.sha(raw));monkeypatch.setattr(a,'RELEASE_DIGEST',a.sha(release))
    ms=[]
    for x in meta:
        fields={k:dict(seal_index=0,member='raw.json',keys=['text'] if k=='text' else ['codes',x['id']]) for k in (('text','code','original_code') if x['id'] in wanted else ('text','code'))}
        ms.append(dict(id=x['id'],fields=fields))
    diag={k:dict(seal_index=0,member='raw.json',keys=[k]) for k in ('achieved_counts','truth_probes')}
    out=bundle('out',{'MEASUREMENTS.json':ms,'DIAGNOSTICS.json':diag},experiment='E86',status='COMPLETE',packet_source_sha256=a.sha(packet),private_join_sha256=a.sha(private),route_verified=True,redaction_audit_complete=True,original_subsample_ids=sorted(wanted),source_seals=[dict(seal=str(raw),sha256=a.sha(raw))])
    s=dict(release=str(release),private_join=str(private),packet_source_seal=str(packet),output_seal=str(out),output_sha256=a.sha(out))
    xs,old,ids,ds=a.inputs(s);assert len(xs)==800 and len(old)==len(ids)==200 and ds['achieved_counts']==counts
    (raw.parent/'raw.json').write_text('{}')
    with pytest.raises(ValueError,match='member mismatch'):a.inputs(s)

def test_once_guard_cannot_choose_second_output(tmp_path):
    s=dict(guard=str(tmp_path/'guard'),analysis=str(tmp_path/'out'),output_sha256='synthetic')
    a.core.claim(s,'synthetic');s['analysis']=str(tmp_path/'other')
    with pytest.raises(FileExistsError):a.core.claim(s,'synthetic')
