import pytest
from .e109_intake import make_units


def fixture():
    original=[];records=[]
    for row in ('fact_recall','language_plan'):
        for i in range(84):
            original.append(dict(row=row,item_id=str(i),property='state',values=dict(A='first',B='second'),target='CPU_ONLY'))
            for layer in (44,52,60):
                for condition in ('steered','random'):
                    records.append((dict(member='jobs.json',index=len(records)),dict(id=f'{row}:{i}:{layer}:{condition}',base_id=str(i),row=row,split='test',reader='oracle',layer=layer,condition=condition,text='The state is first.',malformed=False)))
    return records,original


def test_all_cells_retained_and_metadata_not_sent():
    records,original=fixture();units,joins=make_units(records,original)
    assert len(units)==1260 and len(joins)==1008
    assert all(set(x['data'])=={'id','property','values','readout'} and len(x['id'])==32 for x in units)
    assert all('CPU_ONLY'not in str(x)for x in units)


def test_partial_or_duplicate_readouts_are_ineligible():
    records,original=fixture()
    with pytest.raises(ValueError):make_units(records[:-1],original)
    with pytest.raises(ValueError):make_units(records+[records[0]],original)
