import pytest
from projects.g_agreement.e97.taxonomy import compare


def fixture():
    return [dict(row=str(i),reported=i<20,j_reported=i<20,
                 taxonomy='continuation constraint' if i%2==0 else 'numerical coordinate') for i in range(40)]


def test_paired_bootstrap_and_identical_forecasts():
    rows=fixture();r=compare(rows)
    assert r['verdict']=='MET' and r['delta']==.5 and r['paired_row_bootstrap_95'][0]>0
    for x in rows:x['j_reported']=x['taxonomy']=='continuation constraint'
    r=compare(rows)
    assert r['delta']==0 and r['paired_row_bootstrap_95']==[0,0] and r['falsifier']


def test_no_ladder_denominator_inflation_or_missing_truth_class():
    rows=fixture()
    with pytest.raises(ValueError):compare(rows+rows)
    rows[1]['row']=rows[0]['row']
    with pytest.raises(ValueError):compare(rows)
    rows=fixture()
    for x in rows:x['reported']=True
    assert compare(rows)['verdict']=='NOT EVALUABLE'
