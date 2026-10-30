import pytest
from .d5_analysis import aggregate, join_grid, exclusive


def r(row, item, category='topic_content', attempts=0):
    return dict(bank='E49', row=row, item_id=item, category=category, attempts=attempts)


def test_exclusion_pooling_and_flags():
    data=[r('a','1'),r('a','2',None,2)]+[r('b',str(i),'generic_other') for i in range(3)]
    x=aggregate(data)
    assert x['rows'][0]['kept']==1 and x['rows'][0]['unparseable']==1
    assert x['rows'][0]['categories']['topic_content']['share']==1
    assert x['rows'][0]['flagged_over_5_percent']
    assert x['pooled']['unparseable']==1 and x['pooled']['kept']==4
    assert x['pooled']['readout_weighted']['topic_content']['share']==.25
    assert x['pooled']['equal_row']['topic_content']['share']==.5
    assert x['pooled']['retry_requests']==2
    boundary=[r('x',str(i)) for i in range(19)]+[r('x','missing',None,2)]
    assert not aggregate(boundary)['rows'][0]['flagged_over_5_percent']


def test_repetitions_are_clustered_and_reproducible():
    # One item with opposing repeats has no bootstrap uncertainty.
    data=[r('a','same','topic_content'),r('a','same','generic_other')]
    x=aggregate(data)
    assert x==aggregate(data)
    for k in ['topic_content','generic_other']:
        assert x['rows'][0]['categories'][k]['ci95']==[.5,.5]
    assert x['rows'][0]['n_items']==1


def test_all_missing_not_zero_or_silently_dropped():
    x=aggregate([r('a','1',None,2),r('b','2')])
    assert x['rows'][0]['categories']['topic_content']['share'] is None
    assert x['pooled']['equal_row']['topic_content']['share'] is None
    assert x['pooled']['equal_row']['topic_content']['undefined_draws']==2000
    assert x['pooled']['readout_weighted']['topic_content']['share']==1


def test_exact_grid_and_exclusive_guard(tmp_path):
    keys=[dict(opaque_id='x',bank='E49',row='a',item_id='i')]
    inventory=dict(rows=[dict(bank='E49',row='a',n_readouts=1,n_items=1,source_ids=['i'])])
    judgments=[dict(job='D5_E49',id='x',status='KEPT',attempts=0,code=dict(id='x',category='topic_content'))]
    assert join_grid(keys,judgments,inventory)==[r('a','i')]
    with pytest.raises(ValueError):join_grid(keys,judgments*2,inventory)
    with pytest.raises(ValueError):join_grid(keys,[],inventory)
    judgments[0].update(status='UNPARSEABLE',code=None,attempts=1)
    with pytest.raises(ValueError):join_grid(keys,judgments,inventory)
    p=tmp_path/'guard';exclusive(p,{})
    with pytest.raises(FileExistsError):exclusive(p,{})


def test_once_only_runner_synthetic_504(tmp_path, monkeypatch):
    import json
    from . import d5_analysis as m
    monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(m,'HERE',tmp_path)
    keys=[dict(opaque_id=str(i),bank='E49',row='synthetic',item_id=str(i)) for i in range(504)]
    terminal=[dict(job='D5_E49',id=str(i),status='KEPT',attempts=0,
                   code=dict(id=str(i),category='topic_content')) for i in range(504)]
    inventory=dict(rows=[dict(bank='E49',row='synthetic',n_readouts=504,n_items=504,
                              source_ids=[str(i) for i in range(504)])],pending_bank_adjudications=['W1'])
    for name,value in [('key',keys),('terminal',terminal),('inventory',inventory),
                       ('ANALYSIS_SOURCE_SEAL.json',{}),('ANALYSIS_COMMAND.json',{})]:
        (tmp_path/name).write_text(json.dumps(value))
    spec={k:str(tmp_path/k) for k in ['key','terminal','inventory']}
    spec.update(guard='guard',out='out',terminal_seal_sha256='synthetic')
    m.run(spec)
    assert (tmp_path/'out/RESULT_SEAL.json').exists()
    with pytest.raises(ValueError,match='already attempted'):m.run(spec)
