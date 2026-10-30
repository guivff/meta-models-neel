import pytest
from .e100e_intake import make_units


def fixture():
    labels=[];records=[]
    for row in ('container_after_move','holder_after_handovers'):
        for i in range(84):
            ident=f'{row}:{i}';donor=f'{row}:{i^1}'
            labels.append(dict(id=ident,row=row,split='test',donor_id=donor,source_value=str(i%2),donor_value=str((i^1)%2),source_label='CPU_PRIVATE'))
            for reader in ('oracle','nla'):records.append((dict(member='batch.json',keys=[len(records),'text']),dict(id=ident+reader,item_id=ident,row=row,reader=reader,repeat=0,condition='transplant',text='The value is one.')))
    return records,labels


def test_actual_donor_value_orientation_identical_for_both_readers_no_private_labels():
    records,labels=fixture();units,joins,audit,raw=make_units(records,labels)
    assert len(units)==420 and len(joins)==336 and sum(u['kind']=='old_value'for u in units)==84
    assert units[0]['data']['values']==dict(A='0',B='1') and units[1]['data']['values']==dict(A='0',B='1')
    assert all(x['target_letter']=='B'for x in joins) and 'CPU_PRIVATE'not in str(units)
    assert audit['redacted_records']==0 and not raw


def test_partial_grid_or_wrong_donor_binding_rejected():
    records,labels=fixture()
    with pytest.raises(ValueError):make_units(records[:-1],labels)
    labels[0]['donor_value']='invented'
    with pytest.raises(ValueError):make_units(records,labels)
