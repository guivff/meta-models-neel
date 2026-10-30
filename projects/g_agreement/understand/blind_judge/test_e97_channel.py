import pytest
from .e97_channel import channels
from .rubric202 import original_ids,BASE,amended

def records():return [dict(id=f'{i:032x}',property=dict(definition='Frozen property',values=dict(A='one',B='two')),readout='native text') for i in range(6668)]

def test_full_grid_exact_rubrics_seeded_old_check():
    rows=records();out=channels(rows)
    assert len(out[0][1])==6668 and len(out[1][1])==1667
    assert out[0][2].encode()==amended() and out[1][2]==BASE.read_text()
    assert sorted(x['id'] for x in out[1][1])==original_ids([x['id'] for x in rows],'E97')
    assert [x['readout'] for x in out[0][1]]==[x['readout'] for x in rows]

def test_no_partial_or_label_metadata():
    with pytest.raises(ValueError):channels(records()[:-1])
    rows=records();rows[0]['label']=1
    with pytest.raises(ValueError):channels(rows)
