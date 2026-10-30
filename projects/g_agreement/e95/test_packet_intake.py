import hashlib
import pytest
from projects.g_agreement.e95.packet_intake import row_values,grouped


def fixture():
    unit='a'*32
    row=dict(row_index=0,row='synthetic',item_ids=[unit],oracle_layers=[36,44,56])
    item=dict(id=unit,global_index=0,read_index=2,ids=[1,2,3])
    records=[dict(unit_id=unit,global_index=0,reader='oracle',arm='real',layer=44,
                  position=2+o,position_offset=o,text=f'Synthetic {o}')for o in(-2,-1,0)]
    return row,item,records


def test_source_group_retains_all_ragged_positions_in_exact_order():
    row,item,records=fixture()
    group=grouped(row,'real','oracle',44,item['id'],list(reversed(records)),item,dict(A='one',B='two'))
    assert group['positions']==[dict(offset=x['position_offset'],readout=x['text'])for x in records]
    for malformed in (records[:-1],records+[records[0]], [dict(records[0],position=99)]+records[1:]):
        with pytest.raises(ValueError):grouped(row,'real','oracle',44,item['id'],malformed,item,dict(A='one',B='two'))


def test_literal_value_orientation_matches_e87_and_ambiguous_values_stop():
    records=[dict(feature='f',label=1,value='one'),dict(feature='f',label=0,value='two')]
    assert row_values(records,'f')==dict(A='one',B='two')
    with pytest.raises(ValueError):row_values(records+[dict(feature='f',label=1,value='three')],'f')
