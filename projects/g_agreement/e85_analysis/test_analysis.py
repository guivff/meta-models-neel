import copy
import pytest
from . import rules as r,adapter as a

def rows(n=20):
    return [dict(id=f'{reader}:{i}:{g}:{d}',matched_set=i,genre=g,addressed=d,reader=reader,a=bool(g),b=bool(d),c=False,original=bool(d),original_selected=True) for reader in ('oracle','nla') for i in range(n) for g,d in r.CELLS]

def test_factorial_effects():
    z=r.summarize([x for x in rows() if x['reader']=='oracle'],'a')
    assert z['effects']['genre']==dict(estimate=1,CI95=[1,1])
    assert z['effects']['addressed']==dict(estimate=0,CI95=[0,0])
    assert z['effects']['genre_minus_addressed']==dict(estimate=1,CI95=[1,1])
    assert z['cells']['genre=1,addressed=0']['Wilson95'][1]==1

def test_quartets_resampled_together():
    xs=[x for x in rows() if x['reader']=='oracle']
    for x in xs:x['a']=bool(x['matched_set']%2)
    z=r.summarize(xs,'a')
    assert z['cells']['genre=0,addressed=0']['CI95'][0]<.5
    assert all(v['CI95']==[0,0] for v in z['effects'].values())

def test_missing_separate_masks_no_complete_case_or_zero():
    xs=[x for x in rows() if x['reader']=='oracle'];xs[2]['a']=None
    z=r.summarize(xs,'a')
    assert z['cells']['genre=1,addressed=0']['missing']==1
    assert z['cells']['genre=1,addressed=1']['kept']==20
    assert z['effects']['genre']['estimate']==1
    for x in xs:
        if (x['genre'],x['addressed'])==(1,0):x['a']=None
    z=r.summarize(xs,'a')
    assert r.verdict(z['effects'],1)['R_E1']=='NOT EVALUABLE'

def effects(g=.20,a=.05,lo=.001):
    return dict(genre=dict(estimate=g,CI95=[g,g]),addressed=dict(estimate=a,CI95=[a,a]),genre_minus_addressed=dict(estimate=g-a,CI95=[lo,.4]))

def test_rule_boundaries_and_probe_gate():
    assert r.verdict(effects(),.90)['R_E1']=='MET'
    assert r.verdict(effects(),.8999)['R_E1']=='NOT EVALUABLE'
    assert r.verdict(effects(),None)['R_E1']=='NOT EVALUABLE'
    assert r.verdict(effects(lo=0),1)['R_E1']=='NOT MET'
    assert r.verdict(effects(g=.199),1)['R_E1']=='NOT MET'
    assert r.verdict(effects(a=.051),1)['R_E1']=='NOT MET'
    assert r.verdict(effects(g=.20,a=.20),1)['falsifier']=='MET'
    assert r.verdict(effects(g=.20,a=.20),.8)['falsifier']=='NOT EVALUABLE'

def probes():return [dict(name=n,layer=l,status='COMPLETE',test_auroc=.95) for n in ('genre','addressed') for l in (42,44)]

def test_a_alone_and_layer_specific_gate():
    ps=probes();next(p for p in ps if p['name']=='addressed' and p['layer']==42)['test_auroc']=.8
    z=r.analyze(rows(),ps,{},{});assert z['readers']['oracle']['rules']['R_E1']=='MET'
    assert z['readers']['nla']['rules']['R_E1']=='NOT EVALUABLE'
    assert z['readers']['oracle']['genre_vocabulary_b']['effects']['addressed']['estimate']==1
    assert z['readers']['oracle']['original_rubric']['original']['effects']['addressed']['estimate']==1

def test_incomplete_and_duplicate_quartets():
    xs=[x for x in rows() if x['reader']=='oracle']
    with pytest.raises(ValueError,match='quartets'):r.summarize(xs[:-1],'a')
    with pytest.raises(ValueError,match='duplicate'):r.summarize(xs+[xs[0]],'a')

def code(a=True,b=False,c=False):
    return dict(a_model_self_evaluated=a,b_evaluation_genre_vocabulary=b,c_absent_genre_named=c,a_evidence='evaluated' if a else '',b_evidence='benchmark' if b else '',c_evidence='README' if c else '',c_genres=['README'] if c else [])

def test_judge205_schema_evidence_and_missing():
    assert a.codes(code(), 'evaluated')==dict(a=True,b=False,c=False)
    assert a.codes(None,'whatever')==dict(a=None,b=None,c=None)
    with pytest.raises(ValueError,match='evidence'):a.codes(code(),'not an evidence span')
    assert a.original_code(dict(id='o',eval_mention=False,evidence=''),'anything') is False

def private():
    return [dict(public_id=f'{i}:{g}:{d}',id=f'{i}:{g}:{d}',matched_set=i,genre=g,addressed=d,split='test' if i<100 else 'dev') for i in range(150) for g,d in r.CELLS]

def test_exact_inventory_and_split_separation():
    p=private();assert len(a.inventory(p))==600
    p[0]['split']='dev'
    with pytest.raises(ValueError,match='split-disjoint'):a.inventory(p)
    with pytest.raises(ValueError,match='600'):a.inventory(private()[:-1])

def test_source_gate_before_read(monkeypatch):
    monkeypatch.setattr(a,'committed',lambda:(_ for _ in ()).throw(ValueError('uncommitted')))
    monkeypatch.setattr(a,'read',lambda _:pytest.fail('output IO before commit'))
    monkeypatch.setattr('sys.argv',['e85','--spec','never'])
    with pytest.raises(ValueError,match='uncommitted'):a.main()

def test_sealed_full_grid_roundtrip_and_tamper(tmp_path,monkeypatch):
    def bundle(name,files,**meta):
        p=tmp_path/name;p.mkdir()
        for k,v in files.items():a.write(p/k,v)
        a.core.seal(p,'SEAL.json',**meta);return p/'SEAL.json'
    private_path=tmp_path/'private.json';a.write(private_path,private())
    cfg=tmp_path/'results/g_agreement/understand/e85/CPU_CONFIG.json';cfg.parent.mkdir(parents=True);a.write(cfg,dict(private_sha256=a.sha(private_path),input_seal_sha256='synthetic-input'))
    raw=bundle('raw',{'raw.json':dict(text='evaluated',code=code(),original_code=dict(id='opaque',eval_mention=True,evidence='evaluated'),probes=probes(),bow={k:dict(test_auroc=1) for k in ('genre','addressed')},behaviour=None)})
    wanted=a.original_ids([x['public_id']+r for x in private() if x['split']=='test' for r in ('oracle','nla')])
    ms=[]
    for x in private():
        if x['split']=='dev':continue
        for reader in ('oracle','nla'):
            ident=x['public_id']+reader;selected=ident in wanted
            ms.append(dict(id=ident,item_id=x['public_id'],reader=reader,fields={k:dict(seal_index=0,member='raw.json',keys=[k]) for k in (('text','code','original_code') if selected else ('text','code'))}))
    diag={k:dict(seal_index=0,member='raw.json',keys=[k]) for k in ('probes','bow','behaviour')}
    op=bundle('out',{'MEASUREMENTS.json':ms,'DIAGNOSTICS.json':diag},experiment='E85',status='COMPLETE',input_seal_sha256='synthetic-input',private_sha256=a.sha(private_path),route_verified=True,redaction_audit_complete=True,judge205_sha256=a.sha(a.JUDGE),original_rubric_comparison_verified=True,original_subsample_ids=sorted(wanted),source_seals=[dict(seal=str(raw),sha256=a.sha(raw))])
    monkeypatch.setattr(a,'ROOT',tmp_path)
    s=dict(private=str(private_path),output_seal=str(op),output_sha256=a.sha(op))
    xs,ds=a.inputs(s);assert len(xs)==800 and sum(x['original_selected'] for x in xs)==200
    assert ds['probes']==probes()
    (raw.parent/'raw.json').write_text('{}')
    with pytest.raises(ValueError,match='member mismatch'):a.inputs(s)

def test_once_guard_rejects_alternate_output(tmp_path):
    s=dict(guard=str(tmp_path/'guard'),analysis=str(tmp_path/'out'),output_sha256='synthetic')
    a.core.claim(s,'synthetic');s['analysis']=str(tmp_path/'other')
    with pytest.raises(FileExistsError):a.core.claim(s,'synthetic')


def test_original_sample_matches_frozen_hash_selection():
    import hashlib
    ids=[str(i) for i in range(800)]
    expected=set(sorted(ids,key=lambda x:hashlib.sha256(('20261028:E85:'+x).encode()).digest())[:200])
    assert a.original_ids(ids[::-1])==expected
