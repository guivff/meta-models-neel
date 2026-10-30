import pytest
from . import late as a

def fixture(e):
    out=[]
    for reader in (('oracle','nla') if e=='E70' else ('oracle',)):
        for row in (*a.ROWS,'prose_sentiment') if e=='E70' else a.ROWS:
            for cell in (('1',) if row=='prose_sentiment' else ('1','2','4')) if e=='E70' else ('36','40'):
                for i in range(16 if e=='E70' else 84):
                    out.append(dict(id=f'{reader}:{row}:{cell}:{i}',item=f'{row}:{i}',unit=f'{row}:{i//2}' if e=='E70' else str(i),
                        reader=reader,row=row,cell=cell,sign=1 if i%2 else -1,score=int(row=='prose_sentiment'),truncated=False))
    return out

def test_carriers_both_signs_and_missingness():
    rows=fixture('E70');a.validate(rows,'E70');assert a.analyze(rows,'E70')['oracle']['R_D1']=='MET'
    xs=[x for x in rows if (x['reader'],x['row'],x['cell'])==('oracle',a.ROWS[0],'1')]
    for x in xs:x['score']=x['sign']
    assert a.carrier_rate(xs)['CI95']==[0,0]
    xs[0]['score']=None;assert a.carrier_rate(xs)['estimate']==pytest.approx(1/15)
    for x in rows:
        if x['row']=='prose_sentiment':x['score']=0
    assert a.analyze(rows,'E70')['oracle']['R_D1']=='NOT MET'
    with pytest.raises(ValueError):a.validate(rows[:-1],'E70')

def test_earlier_layer_is_descriptive():
    rows=fixture('E72');a.validate(rows,'E72')
    v=a.analyze(rows,'E72')['oracle'];assert len(v['rates'])==6 and 'R_D1' not in v
    assert not any(x['S_at_least_point20'] for x in v['rates'].values())
