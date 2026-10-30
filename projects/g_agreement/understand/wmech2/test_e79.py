import json
import pytest
from . import e79 as a
from . import core as c

def fixture():
    rows=[]
    for row in sorted(a.ROWS):
        for direction,alpha in [('none',0)]+[(d,v) for d in ('J','nonJ','random') for v in a.DOSES]:
            for i in range(84):
                rows.append(dict(id=f'{row}:{direction}:{alpha}:{i}',row=row,item=str(i),direction=direction,
                     alpha=alpha,target='A' if i%2 else 'B',reader='oracle',property=row,
                     values=dict(A='one',B='three'),text='one',score=1 if direction=='J' else 0,redacted=False))
    return rows

def test_full_grid_and_thresholds():
    rows=fixture();a.validate_grid(rows);r=a.analyze(rows)
    assert r['R_C1']=='MET' and r['passing_states']==3
    for x in rows: x['score']=int(x['direction']=='J' and x['alpha']==4)
    r=a.analyze(rows)
    assert r['R_C1']=='NOT MET' and r['falsifier'] is True
    for x in rows:
        if x['direction']=='J' and x['alpha']==.25: x['score']=1
    assert a.analyze(rows)['R_C1']=='MET'

def test_pairing_and_missingness():
    x={str(i):i%2 for i in range(84)}
    assert c.stats(x,x)['CI95']==[0,0]
    y=dict(x);y['0']=None
    assert c.stats(x,y)['estimate']==pytest.approx(.5-42/83)
    assert c.stats(dict.fromkeys(x,None))['estimate'] is None
    with pytest.raises(ValueError): c.stats(x,{'other':1})

def test_reject_missing_duplicate_target_and_unparseable():
    rows=fixture()
    with pytest.raises(ValueError): a.validate_grid(rows[:-1])
    rows[1]['target']=rows[0]['target']
    with pytest.raises(ValueError): a.validate_grid(rows)
    j=dict(id='x',category='states_value',values=['A'],evidence='one')
    assert c.score(j,'A','one')==1 and c.score(j,'B','one')==-1
    j.update(category='UNPARSEABLE',values=[],evidence='')
    assert c.score(j,'A','one') is None

def test_blind_roundtrip_and_global_once(tmp_path):
    rows=fixture();out=tmp_path/'blind';private=tmp_path/'private.json'
    c.export(rows,out,private,'f'*64,'a'*40)
    packet=c.read(out/'JUDGE_PACKET.json');wire=c.read(out/'WIRE_PACKET.json')
    assert len(packet)==4032 and all(set(x)=={'id','property','values','readout'} for x in packet)
    assert all(set(x)=={'id','readout','rubric'} for x in wire)
    assert private.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError): c.export(rows,out,private,'f'*64,'a'*40)
    js=tmp_path/'judgments';js.mkdir()
    c.write(js/'JUDGMENTS.json',[dict(id=x['id'],category='states_value',values=['A'],evidence='one') for x in packet])
    c.seal(js,'JUDGMENT_SEAL.json',blind_seal_sha256=c.sha(out/'BLIND_SEAL.json'),
           route_verified=True,redaction_audit_complete=True,redacted_opaque_ids=[])
    s=dict(blind=str(out),private=str(private),output_sha256='f'*64,judgments=str(js),
           analysis=str(tmp_path/'analysis'),guard=str(tmp_path/'fixed.guard'))
    joined,_=c.load_codes(s);a.validate_grid(joined)
    assert {x['score'] for x in joined}=={-1,1}
    c.claim(s,'a'*40);s['analysis']=str(tmp_path/'alternate')
    with pytest.raises(FileExistsError): c.claim(s,'a'*40)
    packet[0]['readout']='changed';c.write(out/'JUDGE_PACKET.json',packet)
    with pytest.raises(ValueError): c.load_codes(s)

def test_not_evaluable_and_alpha4_missing():
    rows=fixture()
    for x in rows: x['score']=None if x['alpha']==4 else 0
    assert a.analyze(rows)['R_C1']=='NOT MET'
    for x in rows:
        if x['direction']=='J': x['score']=None
    assert a.analyze(rows)['R_C1']=='NOT EVALUABLE'
