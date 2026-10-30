import pytest
from score94 import value_class,claim_class,join,point,summarize,fraction
from run_once94 import analyse

def code(v=None,category=None):
    v=[] if v is None else v
    return dict(category=category or ('states_value' if v else 'silent'),values=v)
def row(unit,reader,c,bank='B',cluster=None,stratum='text'):
    return dict(bank=bank,unit=unit,reader=reader,**{'class':c},cluster=cluster or bank+'|'+unit,stratum=stratum,raw_category='synthetic',both_values=False)
def pairs(outcomes):
    return [dict(bank='B',unit=str(i),cluster=str(i),oracle=a,nla=b) for i,(a,b) in enumerate(outcomes)]
def test_binary_truth_both_polarities():
    assert value_class(code(['A']),'A')=='correct'
    assert value_class(code(['B']),'A')=='wrong'
    assert value_class(code(['B']),'B')=='correct'
    assert value_class(code(['A']),'B')=='wrong'
def test_neutral_both_and_missing_distinct():
    assert value_class(code(['A','B']),'A')=='no mention'
    assert value_class(code(),'B')=='no mention'
    assert value_class(code(category='UNPARSEABLE'),'A') is None
    with pytest.raises(ValueError):value_class(code(['A'],category='silent'),'A')
def test_claim_precedence_and_generic():
    assert claim_class(dict(generic=False,claims=[dict(verdict='SUPPORTED'),dict(verdict='CONTRADICTED')]))=='wrong'
    assert claim_class(dict(generic=False,claims=[dict(verdict='SUPPORTED')]))=='correct'
    assert claim_class(dict(generic=True,claims=[]))=='no mention'
    assert claim_class(None) is None

def test_intersection_excludes_missing_not_silence():
    rs=[row('a','oracle','correct'),row('a','nla','correct'),row('b','oracle',None),row('b','nla','wrong'),row('c','nla','no mention')]
    p,a=join(rs);assert len(p)==1 and a['identity_intersection']==2 and a['UNPARSEABLE_oracle']==1 and a['unmatched_nla']==1
    with pytest.raises(ValueError):join(rs+[rs[0]])
def test_no_mentions_agree_without_reporting():
    m=point(pairs([('no mention','no mention')]*4));assert m['agreement']['rate']==1 and m['ensemble']['coverage']['rate']==0 and m['ensemble']['precision']['rate'] is None
    assert m['H_A1']['status']=='NOT EVALUABLE'
def test_disagreement_and_ensemble_denominators():
    m=point(pairs([('correct','correct'),('wrong','wrong'),('no mention','no mention'),('correct','wrong'),('wrong','correct'),('wrong','no mention')]))
    assert m['agreement']['rate']==.5 and m['ensemble']['precision']['rate']==.5
    assert m['ensemble']['coverage']['rate']==pytest.approx(1/3)
    assert m['readers']['oracle']['precision']['rate']==.4
    assert m['readers']['oracle']['marginal_accuracy']['rate']==pytest.approx(1/3)
    assert m['disagreements']==dict(n=3,oracle_right=1,nla_right=1,neither_right=1)
def test_hypothesis_threshold_without_new_significance_rule():
    m=point(pairs([('correct','correct')]*6+[('wrong','wrong')]*4+[('correct','wrong')]*5))
    assert m['H_A1']['difference']==pytest.approx(.6-11/15)
    assert m['H_A1']['status']=='NOT MET'
    m=point(pairs([('correct','correct')]*5+[('wrong','no mention')]*5));assert m['H_A1']['difference']==.5 and m['H_A1']['status']=='MET'
def test_empty_and_wilson():
    assert point([])['H_A1']['status']=='NOT EVALUABLE'
    assert fraction(0,0)['Wilson95'] is None
    assert fraction(5,10)['Wilson95'][0]<.5<fraction(5,10)['Wilson95'][1]
def test_bootstrap_deterministic_clusters():
    p=pairs([('correct','correct'),('wrong','wrong'),('correct','no mention')]);p[1]['cluster']=p[0]['cluster']
    a=summarize(p,draws=100);assert a==summarize(p,draws=100)
    assert a['H_A1']['cluster_count']==2
    assert a['H_A1']['undefined_draws']>=0

def test_grounded_pool_excludes_claims_and_placebo():
    rs=[]
    for bank in ('E56','E67_wave1','E67_wave2','E76'):
        rs.extend([row('x','oracle','correct',bank),row('x','nla','correct',bank)])
    r=analyse(rs);assert r['pooled_value_grounded']['n']==1 and len(r['banks'])==4

def test_different_arms_and_same_cluster():
    rs=[row('x|own','oracle','correct',cluster='shared'),row('x|own','nla','wrong',cluster='shared'),row('x|swap','oracle','wrong',cluster='shared')]
    p,a=join(rs);assert len(p)==1 and a['unmatched_oracle']==1

def test_value_source_schema_and_opposite_E73_label_convention(tmp_path,monkeypatch):
    import sources94 as s,json
    def put(path,obj):path.write_text(json.dumps(obj));return str(path)
    private=put(tmp_path/'labels.json',[dict(id='u',label=1,feature='r')]);key=put(tmp_path/'key.json',[dict(opaque_id=r,source_id='u:'+r+':0',unit_id='u',eval=False) for r in ('oracle','nla')]);js=put(tmp_path/'judgments.json',[dict(id=r,category='states_value',values=['A'],evidence='A') for r in ('oracle','nla')])
    spec=dict(private_items=private,private_key=key,judgments=js)
    rows=s.load(dict(banks=[dict(type='value',bank='E57',spec=spec)]));assert all(r['class']=='correct' for r in rows)
    key73=put(tmp_path/'key73.json',[dict(opaque_id=r,source_id='u',reader=r,label=0,state='r') for r in ('oracle','nla')])
    rows=s.load(dict(banks=[dict(type='E73',bank='E73',stratum='structural',key=key73,judgments=js)]));assert all(r['class']=='correct' for r in rows)
    assert len(join(rows)[0])==1

def test_once_runner_creates_seal_and_blocks_repeat(tmp_path,monkeypatch):
    import run_once94 as r,json,hashlib
    here=tmp_path/'public';cache=tmp_path/'cache';here.mkdir();cache.mkdir()
    data=cache/'SOURCES.PRIVATE.json';data.write_text(json.dumps(dict(files={},unavailable={})))
    (here/'CODE_SEAL.json').write_text(json.dumps(dict(files={})))
    (here/'E67_SCOPE.json').write_text(json.dumps(dict(status='RATIFIED')))
    (here/'INPUT_PLAN.json').write_text(json.dumps(dict(private_sources=str(data),private_sources_sha256=hashlib.sha256(data.read_bytes()).hexdigest())))
    monkeypatch.setattr(r,'HERE',here);monkeypatch.setattr(r,'CACHE',cache)
    monkeypatch.setattr(r,'load',lambda _: [row('x','oracle','correct'),row('x','nla','correct')])
    r.main();seal=json.loads((here/'analysis_once_20261028/ANALYSIS_SEAL.json').read_text())
    for name,digest in seal['files'].items():assert hashlib.sha256((here/'analysis_once_20261028'/name).read_bytes()).hexdigest()==digest
    assert (cache/'ITEM_CLASSES.PRIVATE.json').stat().st_mode&0o777==0o600
    with pytest.raises(FileExistsError):r.main()

def test_tampered_source_stops_before_claim(tmp_path,monkeypatch):
    import run_once94 as r,json,hashlib
    here=tmp_path/'public';here.mkdir();source=tmp_path/'source';source.write_text('changed')
    data=tmp_path/'private';data.write_text(json.dumps(dict(files={str(source):'0'*64})))
    (here/'CODE_SEAL.json').write_text(json.dumps(dict(files={})))
    (here/'E67_SCOPE.json').write_text(json.dumps(dict(status='RATIFIED')))
    (here/'INPUT_PLAN.json').write_text(json.dumps(dict(private_sources=str(data),private_sources_sha256=hashlib.sha256(data.read_bytes()).hexdigest())))
    monkeypatch.setattr(r,'HERE',here)
    with pytest.raises(ValueError,match='source drift'):r.main()
    assert not (here/'analysis_once_20261028').exists()

def test_E67_wave_namespaces_and_exact_prompt_identity(tmp_path):
    import sources94 as s,json
    banks=[]
    for wave in (1,2):
        grids={};pairs=[]
        for packet,reader in enumerate(('oracle','nla'),1):
            folder=tmp_path/f'w{wave}_p{packet}';folder.mkdir();records=[]
            for cond in ('matched','mismatched'):
                opaque=reader+'_'+cond
                records.append(dict(condition=cond,id=opaque,packet=packet,prompt_arm='native',prompt_item_id='own' if cond=='matched' else reader+'_donor',prompt_sha256='same' if cond=='matched' else reader+'_hash'))
            pairs.append(dict(bank='E56',reader=reader,arm='native',item_id='own',records=records))
            (folder/'JUDGMENTS.json').write_text(json.dumps([dict(id=r['id'],status='KEPT',code=dict(id=r['id'],generic=False,claims=[dict(verdict='SUPPORTED')])) for r in records]))
            grids[str(packet)]=dict(dir=str(folder))
        mapping=tmp_path/f'map{wave}.json';mapping.write_text(json.dumps(dict(pairs=pairs)))
        banks.append(dict(type='E67',bank='E67',wave=wave,map=str(mapping),grids=grids))
    rows=s.load(dict(banks=banks));out=analyse(rows)
    assert set(out['banks'])=={'E67_wave1','E67_wave2'}
    assert out['pooled_value_grounded']['n']==0
    for b in out['banks'].values():
        assert b['metrics']['n']==1
        assert b['pairing']['unmatched_oracle']==1 and b['pairing']['unmatched_nla']==1
