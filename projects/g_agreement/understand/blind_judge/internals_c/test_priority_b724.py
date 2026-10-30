from copy import deepcopy
from decimal import Decimal
import signal
from .priority_b724 import park


def test_pause_only_own_waiting_unreserved_ticket_preserves_other_banks_and_pacing():
    state=dict(waiting=[dict(pid=1,bank='E118',ticket='one'),dict(pid=2,bank='E127',ticket='two'),dict(pid=3,bank='E79_ARM_B',ticket='three')],interval_seconds=2,bank_sends={'E118':10},next_send_epoch=7)
    calls=[];out=park(state,{'low':dict(pid=1,bank='E118')},lambda p:(Decimal('.1'),Decimal(0)),lambda p,s:calls.append((p,s)))
    assert calls==[(1,signal.SIGSTOP)] and list(out)==['low']
    assert [x['pid'] for x in state['waiting']]==[2,3] and state['interval_seconds']==2 and state['bank_sends']=={'E118':10} and state['next_send_epoch']==7


def test_inflight_or_unknown_reservation_and_nonqueued_worker_never_interrupted():
    state=dict(waiting=[dict(pid=1,bank='E118',ticket='one')]);original=deepcopy(state);calls=[]
    assert park(state,{'low':dict(pid=1,bank='E118')},lambda p:(Decimal('.1'),Decimal('.01')),lambda *x:calls.append(x))=={}
    assert park(state,{'other':dict(pid=2,bank='E124')},lambda p:(0,0),lambda *x:calls.append(x))=={}
    assert state==original and calls==[]
