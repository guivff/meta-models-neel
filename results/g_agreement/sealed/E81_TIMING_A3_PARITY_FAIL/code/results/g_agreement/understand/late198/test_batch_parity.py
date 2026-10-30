import sys
from types import SimpleNamespace
import numpy as np
import pytest
from contract import ROOT, read
from batch_parity import check_outputs, trim_generated
from runtime import Runtime


def test_eight_item_native_batch32_parity(monkeypatch, tmp_path):
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e56/job'))
    import native_nla512
    calls=[]
    class Oracle:
        def verbalize(self,h,layer,k,sampling,batch):
            calls.append((len(h),batch))
            assert batch==32 and layer==44 and k==1
            assert sampling.temperature==0 and sampling.top_p==1 and sampling.max_new_tokens==128
            return [[str(float(x[0]))] for x in h]
    def nla(reader,h,k,batch):
        assert batch==32 and k==1
        calls.append((len(h),batch))
        return [[dict(raw=str(float(x[0])),text=str(float(x[0])),malformed=False)] for x in h]
    monkeypatch.setattr(native_nla512,'native_nla',nla)
    b=Runtime(None);b.native_batch_size=32;b.readers=SimpleNamespace(oracle=Oracle(),nla=object())
    h=np.arange(32*4,dtype=np.float32).reshape(32,4)
    for reader in ('oracle','nla'):
        batch=b.native(reader,h)
        serial=[b.native(reader,h[i:i+1])[0] for i in range(8)]
        check_outputs(batch[:8],serial,tmp_path/(reader+'.json'),list(map(str,range(8))),32)
        assert read(tmp_path/(reader+'.json'))['status']=='PASS'
    assert (32,32) in calls and (1,32) in calls


def test_exact_parity_rejects_changed_token_and_trims_only_after_eos(tmp_path):
    assert trim_generated([1,9,0,0],{9})==[1,9]
    assert trim_generated([1,0,2],{9})==[1,0,2]
    with pytest.raises(ValueError,match='differs from serial'):
        check_outputs([{'token_ids':[1]}],[{'token_ids':[2]}],tmp_path/'bad.json',['opaque'],32)
    assert read(tmp_path/'bad.json')['status']=='FAIL'
