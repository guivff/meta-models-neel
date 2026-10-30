import pytest
from projects.g_agreement.understand import e32_analysis158 as A,e32_shard158 as S
from projects.g_agreement.blindspot import protocol as P


def test_missing_shards(tmp_path):
    p=tmp_path/'plan';P.dump(p,{'row_shards':[['a'],['b']]})
    with pytest.raises(ValueError,match='all shards'):A.merge(p,tmp_path,[],tmp_path/'out')


def test_once_failure(tmp_path):
    p=tmp_path/'spec';P.dump(p,{'lock':str(tmp_path/'lock'),'pins':{str(tmp_path/'missing'):'x'}})
    with pytest.raises(FileNotFoundError):A.run(p,P.sha(p))
    with pytest.raises(FileExistsError):A.run(p,P.sha(p))


def gate_fixture():
    refs={f'r{i}':{'class':'semantic','D':1.} for i in range(9)}
    items=[{'id':f'{f}-{y}','feature':f,'label':y} for f in refs for y in (0,1)]
    records=[dict(id=x['id'],feature=x['feature'],set=cs,arm=arm,score=float(x['label'])) for x in items for cs in ('w1','e30') for arm in ('A','B')]
    return refs,items,records


@pytest.mark.parametrize('failure',[None,'baseline','w1','e30'])
def test_global_validity(failure):
    refs,items,records=gate_fixture()
    if failure:
        for r in records:
            if (failure=='baseline' and r['arm']=='A') or (r['arm']=='B' and r['set']==failure):r['score']=-r['score']
        with pytest.raises(A.InvalidRun):A.global_validity(records,items,refs,[])
    else:assert A.global_validity(records,items,refs,[])['A_reproduces_E25']


def test_invalid_gate_never_opens_science(tmp_path,monkeypatch):
    refs,items,records=gate_fixture()
    for r in records:
        if r['arm']=='A':r['score']=-r['score']
    bank=tmp_path/'bank';bank.mkdir();P.jsonl(bank/'items.jsonl',items);P.dump(bank/'references.json',refs)
    plan=tmp_path/'plan';p={'row_shards':[list(refs)],'high_D_rows':[],'input_seal_sha256':'input','capture_seal_sha256':'capture'};P.dump(plan,p)
    source=tmp_path/'shard';source.mkdir()
    P.dump(source/'BINDING.json',dict(slot=0,rows=list(refs),plan_sha256=P.sha(plan),input_seal_sha256='input'))
    P.dump(source/'STAGE_BINDING.json',{'capture_seal_sha256':'capture'})
    P.dump(source/'SCORE_PARITY_SEAL.json',{'status':'PASS'})
    P.dump(source/'SCORE_SEAL.json',{'files':{n:'' for n in ['scores.jsonl','VALIDITY_INPUTS.jsonl','BINDING.json','STAGE_BINDING.json','SCORE_PARITY_SEAL.json']}})
    P.jsonl(source/'VALIDITY_INPUTS.jsonl',records)
    monkeypatch.setattr(P,'verify',lambda *args:None) # integrity is separate from read-order test
    original=P.rows
    def guarded(path):
        assert path.name!='scores.jsonl','science opened before gate'
        return original(path)
    monkeypatch.setattr(P,'rows',guarded)
    with pytest.raises(A.InvalidRun):A.merge(plan,bank,[source],tmp_path/'merged')
    assert not (tmp_path/'merged').exists()


def test_invalid_analysis_seals_and_keeps_once_lock(tmp_path,monkeypatch):
    plan=tmp_path/'plan';P.dump(plan,{})
    spec=tmp_path/'spec';out=tmp_path/'out'
    P.dump(spec,dict(lock=str(tmp_path/'lock'),pins={},plan=str(plan),bank=str(tmp_path),capture=str(tmp_path),pulls=[],merged=str(tmp_path/'merged'),out=str(out)))
    monkeypatch.setattr(S,'verify_capture',lambda *args:None)
    def invalid(*args):raise A.InvalidRun({'A_reproduces_E25':False})
    monkeypatch.setattr(A,'merge',invalid)
    monkeypatch.setattr(A.A,'analyse',lambda *args:pytest.fail('science analysis ran'))
    A.run(spec,P.sha(spec))
    assert S.E.read(out/'ANALYSIS_SEAL.json')['status']=='INVALID'
    assert not S.E.read(out/'INVALID.json')['shard_results_used']
    with pytest.raises(FileExistsError):A.run(spec,P.sha(spec))


def test_complete_sealed_merge(tmp_path):
    refs={f'r{i}':{'class':'semantic' if i<9 else 'structure','D':1.} for i in range(25)}
    items=[{'id':f'{f}-{i}','feature':f,'label':i%2} for f in refs for i in range(84)]
    bank=tmp_path/'bank';bank.mkdir();P.jsonl(bank/'items.jsonl',items);P.dump(bank/'references.json',refs)
    plan=tmp_path/'plan';groups=[list(refs)[:13],list(refs)[13:]]
    P.dump(plan,dict(row_shards=groups,high_D_rows=[],input_seal_sha256='input',capture_seal_sha256='capture'))
    outputs=[]
    for slot,group in enumerate(groups):
        source=tmp_path/f'shard{slot}';source.mkdir();outputs.append(source)
        records=[dict(id=x['id'],feature=x['feature'],set=cs,arm=arm,score=float(x['label'])) for x in items if x['feature'] in group for cs in ('w1','e30') for arm in S.ARMS]
        P.jsonl(source/'scores.jsonl',records)
        P.jsonl(source/'VALIDITY_INPUTS.jsonl',[r for r in records if r['arm']=='A' or r['arm']=='B' and refs[r['feature']]['class']=='semantic'])
        P.dump(source/'BINDING.json',dict(slot=slot,rows=group,plan_sha256=P.sha(plan),input_seal_sha256='input'))
        P.dump(source/'STAGE_BINDING.json',{'capture_seal_sha256':'capture'})
        P.dump(source/'SCORE_PARITY.json',{})
        S.seal(source,['SCORE_PARITY.json'],'SCORE_PARITY_SEAL.json','PASS')
        S.seal(source,['scores.jsonl','VALIDITY_INPUTS.jsonl','BINDING.json','STAGE_BINDING.json','SCORE_PARITY_SEAL.json'],'SCORE_SEAL.json','COMPLETE_VALIDITY_PENDING')
    merged=tmp_path/'merged';A.merge(plan,bank,outputs,merged)
    P.verify(merged,'SCORE_SEAL.json')
    assert len(P.rows(merged/'scores.jsonl'))==25200
