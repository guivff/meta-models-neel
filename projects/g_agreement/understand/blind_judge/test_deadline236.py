from types import SimpleNamespace
import pytest
from .deadline236 import PAID_CUTOFF,paid_window


def test_exact_cutoff_even_after_pacing_and_restore():
    calls=[];post=lambda *a,**kw:calls.append(1)
    api=SimpleNamespace(requests=SimpleNamespace(post=post));now=[PAID_CUTOFF-1]
    with paid_window(api,clock=lambda:now[0]):
        api.requests.post('unused')
        now[0]=PAID_CUTOFF # a pacing delay can cross deadline after one() entry
        with pytest.raises(ValueError,match='expired'):api.requests.post('unused')
    assert len(calls)==1 and api.requests.post is post


def test_credit_latch_at_post_boundary(tmp_path):
    pause=tmp_path/'PAUSED_402.json';api=SimpleNamespace(requests=SimpleNamespace(post=lambda *a,**kw:pytest.fail('sent while paused')))
    with paid_window(api,pauses=[pause],clock=lambda:0):
        pause.write_text('{}')
        with pytest.raises(ValueError,match='402'):api.requests.post('unused')
