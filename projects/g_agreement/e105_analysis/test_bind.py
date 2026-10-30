import pytest
from . import bind as b
from . import adapter as a
from .rules import ROWS

def fixture(tmp_path):
    def bundle(name,data,**meta):
        p=tmp_path/name;p.mkdir()
        for n,v in data.items():a.write(p/n,v)
        a.core.seal(p,'SEAL.json',**meta);return dict(seal=str(p/'SEAL.json'),sha256=a.sha(p/'SEAL.json'))
    metadata=[dict(id=f'{r}:{i}',row=r) for r in ROWS for i in range(84)]
    inv=bundle('inv',{'INVENTORY.json':metadata})
    rows={}
    for row in ROWS:
        if row=='indent_level':
            rows[row]=dict(status='NOT RUN (operational)',attempts=[bundle('fail'+str(i),{'FAILURE.json':{'attempt':i}},experiment='E105',status='NO_FIT',input_sha256=row,source_sha256='synthetic',gpu_type='synthetic') for i in range(2)])
        else:
            index=[dict(id=f'{row}:{i}',conditions={c:dict(member='raw.json',keys=[i,c]) for c in ('T','S','0')}) for i in range(84)]
            rows[row]=dict(status='COMPLETE',**bundle(row,{'raw.json':{'do_not_parse':'no scores here'},'MEASUREMENT_INDEX.json':index},experiment='E105',status='COMPLETE',input_sha256=row,source_sha256='synthetic',gpu_type='synthetic'))
    return dict(status='E105_RESTART_RESOLVED',rows=rows,input_hashes={r:r for r in ROWS},inventory_seal=inv['seal'],inventory_sha256=inv['sha256'],inventory_commit='a'*40,e100_targets='synthetic',analysis='synthetic')

def test_binder_uses_original_indices_without_reading_scores(tmp_path,monkeypatch):
    p=fixture(tmp_path);original=a.read
    def read(path):
        assert str(path).split('/')[-1] not in ('raw.json','FAILURE.json')
        return original(path)
    monkeypatch.setattr(a,'read',read)
    z=b.build(p,tmp_path/'bound');assert z['items']==420 and z['conditions']==1260 and not z['raw_scores_parsed']
    spec=original(tmp_path/'bound/SPEC.json');s=a.core.verify(spec['output_seal'],spec['output_sha256'])
    assert s['restart_resolution']['rows']['indent_level']['status']=='NOT RUN (operational)'
    assert len(original(tmp_path/'bound/MEASUREMENTS.json'))==420

def test_binder_requires_final_resolution_and_rejects_wrong_input(tmp_path):
    p=fixture(tmp_path);p['status']='PENDING'
    with pytest.raises(ValueError,match='dispositions'):b.build(p,tmp_path/'bound')
    p['status']='E105_RESTART_RESOLVED';p['input_hashes']['format_plan']='wrong'
    with pytest.raises(ValueError,match='input'):b.build(p,tmp_path/'bound')

def test_binder_gate_before_plan_read(monkeypatch):
    monkeypatch.setattr(a,'committed',lambda:(_ for _ in ()).throw(ValueError('uncommitted')))
    monkeypatch.setattr(a,'read',lambda _:pytest.fail('IO before commit'))
    monkeypatch.setattr('sys.argv',['bind','--plan','never','--out','never'])
    with pytest.raises(ValueError,match='uncommitted'):b.main()
