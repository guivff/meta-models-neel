import pytest
from .e123_binding import project
from .e123_close import pointers
from .seal_bank import disposition


def test_readout_ids_join_dispatch_ids_not_order_and_null_not_zero():
    js=[dict(id='b',readout_id='native-b',source_ref={}),dict(id='a',readout_id='native-a',source_ref={})]
    rows=[dict(id='a',kind='original104',status='KEPT',code=dict(id='a')),dict(id='b',kind='original104',status='UNPARSEABLE',code=None)]
    out=project(js,rows,'test',n=2);assert out['native-b']['code_source']['keys']==[1,'code'];assert out['native-a']['judgment_id']=='a'
    assert pointers(rows,'seal','sha',n=2)[1]['status']=='UNPARSEABLE'
    with pytest.raises(ValueError):project(js,rows,'test')
    with pytest.raises(ValueError):disposition(3,.1,.01)
