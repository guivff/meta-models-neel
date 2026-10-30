from . import e78 as a

def test_signed_rates_missing_and_truncation():
    rows=[dict(bank='E49',row='fixture',item=str(i),score=1 if i<42 else 0,truncated=i<9) for i in range(84)]
    r=a.analyze(rows)['rows']['E49:fixture']
    assert r['status']=='REPORTED' and r['estimate']==.5 and r['truncation_over_10_percent']
    for x in rows:x['score']=None
    assert a.analyze(rows)['rows']['E49:fixture']['status']=='NOT EVALUABLE'
    assert len(a.analyze(rows)['ordinal'])==2

def test_explanation_rule():
    assert a.text_record(dict(text='unused',raw='prefix<explanation>one</explanation>end'))==('one',False)
    assert a.text_record(dict(text='<explanation>one'))==('<explanation>one',True)
