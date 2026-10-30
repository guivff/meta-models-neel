import numpy as np
import pytest
from prepare63 import select_ids,gaussian_pool,BANKS

def test_shared_gaussian_is_raw_deterministic_and_not_unit_norm():
    z=gaussian_pool();assert z.shape==(200,5120) and z.dtype==np.float32
    assert np.array_equal(z,gaussian_pool()) and np.linalg.norm(z[0])>50

def test_uniform_complete_universe_and_identity_pairing():
    rows=[{'bank':b,'id':str(i),'split':'test','index':i} for b in sorted(BANKS) for i in range(100)]
    selected=select_ids(rows);assert len({(x['bank'],x['id']) for x in selected})==200
    assert select_ids(list(reversed(rows)))==selected
    with pytest.raises(ValueError):select_ids([x for x in rows if x['bank']!='E59'])

def test_native_one_preserves_raw_vector():
    import torch
    from worker63 import native_one
    class Oracle:
        def verbalize(self,h,layer,k,sampling,batch):
            assert layer==44 and k==1 and h.tolist()==[[2.,3.,4.]]
            return [['raw']]
    b=type('B',(),{'oracle':Oracle()})();h=np.array([[2.,3.,4.]],np.float32)
    assert len(native_one(b,'oracle',h)[0])==1 and h.tolist()==[[2.,3.,4.]]

def test_full_shared_pool_grid(tmp_path,monkeypatch):
    import time
    import worker63
    for name in ('random','shuffled42','shuffled44'):np.save(tmp_path/(name+'.npy'),gaussian_pool())
    out=tmp_path/'out';out.mkdir()
    class Backend:
        def load_oracle(self):pass
        def load_nla(self):pass
    monkeypatch.setattr(worker63,'native_one',lambda b,r,h:[['unused'] for _ in h])
    monkeypatch.setattr(worker63,'native_one',lambda b,r,h:[[{'raw':'raw','text':'raw'} for _ in range(1)] for _ in h])
    worker63.run(tmp_path,Backend(),out,time.time()+1440)
    import json
    for reader in ('oracle','nla'):
        rows=[json.loads(s) for s in (out/(reader+'.jsonl')).read_text().splitlines()]
        assert len(rows)==400 and len({x['vector_id'] for x in rows})==400
        assert len({(x['vector_id'],x['repeat']) for x in rows})==400
