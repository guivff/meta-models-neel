import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.e97.capture import validate, acquire, Clock


def test_public_inventory_and_no_targets():
    xs=[dict(item_id=str(i),split='test' if i<3360 else 'dev',text='x',input_ids=[1],read_position=0) for i in range(6720)]
    assert len(validate(xs))==6720
    xs[0]['label']='A'
    with pytest.raises(ValueError):validate(xs)


def test_capture_keeps_pilot_and_rejects_incomplete_inventory(tmp_path):
    class Backend:
        oracle=SimpleNamespace(tok=SimpleNamespace(encode=lambda *a,**k:[1]))
        def validate_tokenization(self,items):pass
        def capture(self,items):return {l:np.full((len(items),5120),l,dtype=np.float32) for l in (42,44)}
    import time
    items=[dict(id=str(i),ids=[1],text='x') for i in range(9)]
    with pytest.raises(ValueError,match='Complete capture'):
        acquire(items,Backend(),Clock(tmp_path,time.time()+3600),tmp_path)
    assert np.load(tmp_path/'batches/0000.44.npy').shape==(8,5120)
    assert json.loads((tmp_path/'items.order.json').read_text())==[str(i) for i in range(9)]
    assert json.loads((tmp_path/'PROGRESS.json').read_text())['completed_items']==9


def test_clock_refuses_overrun(tmp_path):
    import time
    from projects.g_agreement.e97.capture import NoFit
    clock=Clock(tmp_path,time.time()+121);clock.events=[dict(phase='capture',seconds=10)]
    with pytest.raises(NoFit):clock.forecast(1)
