import pytest
from .late_bank_handoff import assemble


def test_shuffled_terminal_indices_bound_by_id_missing_not_zero():
    joins=[dict(id=str(i),item_id=str(i//2),arm='targeted' if i%2 else 'sham',source_ref=dict(seal='native',member='jobs/x.json',keys=[i,'text'])) for i in range(800)]
    rows=[dict(id=str(i),kind='eval85',status='UNPARSEABLE' if i==3 else 'KEPT',code=None if i==3 else dict(a_model_self_evaluated=False)) for i in reversed(range(800))]
    out,s=assemble('E120',joins,rows,{}, {},dict(seal='native'))
    assert out[3]['fields']['code']['keys']==[796,'code']
    assert out[3]['fields']['block']['keys']==[3,'source_layer']
    with pytest.raises(ValueError):assemble('E120',joins,rows[:-1],{},{},dict(seal='native'))


def test_two_blocks_keep_false_boolean_and_missing_distinct():
    joins=[dict(id=f'{i}:{b}',item_id=str(i),block=b,cohort_index=i) for i in range(376) for b in (52,60)]
    rows=[dict(id=j['id'],kind='choice_hit',status='UNPARSEABLE' if j['id']=='0:52' else 'KEPT',code=None if j['id']=='0:52' else False) for j in reversed(joins)]
    out,_=assemble('E116',joins,rows,{},{},{},{})
    first=next(x for x in out if x['id']=='0');assert first['blocks']['52']['hit']['keys']==[751,'code'];assert first['blocks']['60']['hit']['keys']==[750,'code']
    rows[0]['code']=0
    with pytest.raises(ValueError):assemble('E116',joins,rows,{},{},{},{})
