import numpy as np
import torch
from contextlib import contextmanager
from native_nla512 import native_nla,truncation_summary


def test_per_sequence_close_stop_and_unchanged_prompt_adapter():
    class Tok:
        pad_token_id=0
        def batch_decode(self,x,**kwargs):return ['<explanation>x</explanation>' if row[0].item()==1 else '<explanation>unfinished' for row in x]
    class AV:
        def generate(self,**kw):
            assert kw['input_ids'].tolist()==[[9,8],[9,8]]
            assert kw['do_sample'] is False and kw['max_new_tokens']==512
            result=torch.tensor([[9,8,1],[9,8,2]])
            assert kw['stopping_criteria'](result,None).tolist()==[True,False]
            return result
    class NLA:
        tok=Tok();av=AV();device='cpu';prompt_ids=[9,8]
        @contextmanager
        def _inject(self,x):
            assert x.tolist()==[[2.,3.],[2.,3.]]
            yield
    h=np.array([[2.,3.]],np.float32);out=native_nla(NLA(),h,k=2)
    assert out[0][0]['text']=='x' and out[0][0]['truncated'] is False
    assert out[0][1]['text']=='<explanation>unfinished' and out[0][1]['truncated'] is True
    assert h.tolist()==[[2.,3.]]


def test_truncation_strictly_above_ten_percent():
    records=[{'feature':'a','raw':'<explanation>x</explanation>'} for _ in range(9)]+[{'feature':'a','raw':'open'}]
    s=truncation_summary(records)['rows']['a'];assert s['rate']==.1 and not s['flag_over_10_percent']
    records.append({'feature':'a','raw':'open'});assert truncation_summary(records)['rows']['a']['flag_over_10_percent']
