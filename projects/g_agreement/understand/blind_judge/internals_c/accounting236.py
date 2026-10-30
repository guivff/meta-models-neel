"""Prospective exact registered E127/E128 caps; inherit all prior physical exposure."""
from decimal import Decimal
from .accounting234 import snapshot as previous
from .accounting import bank_actual
from .transport import SHARED
from projects.g_agreement.readerbench.io import read
from projects.g_agreement.readerbench.scoring import require


def snapshot(new_banks=()):
    out=previous(new_banks)
    for bank in ('E127','E128'):
        p=SHARED/bank/'ALLOCATION_C.json'
        if bank in out['open_banks'] or not p.exists() or read(p).get('status')!='OPEN':continue
        a=read(p);require(a['bank']==bank and a['operator']=='W-internals-C' and a['reservation_included'] is True and Decimal(str(a['allocation_usd']))==3,'actual separate registered bank3')
        actual,unknown=bank_actual(SHARED/bank/'ledger');left=max(Decimal(0),Decimal(3)-actual-unknown)
        out['open_banks'][bank]=dict(cap='3',settled_usd=str(actual),physical_unknown_usd=str(unknown),open_usd=str(left))
        for k in ('open_caps_remaining_usd','actual_plus_open_caps_usd'):out[k]=str(Decimal(out[k])+left)
    require(Decimal(out['actual_plus_open_caps_usd'])<=1000,'all evidenced judging exposure<=1000')
    return out
