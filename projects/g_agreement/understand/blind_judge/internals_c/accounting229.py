"""Prospective concrete §228–229 banks; never count an unallocated allowance."""
from decimal import Decimal
from .accounting226 import snapshot as previous
from .accounting import bank_actual
from .transport import SHARED
from projects.g_agreement.readerbench.io import read
from projects.g_agreement.readerbench.scoring import require


def snapshot(new_banks=()):
    out=previous(new_banks)
    for bank,cap in {'E116':2,'E117':4,'E118':1,'E119':3}.items():
        path=SHARED/bank/'ALLOCATION_C.json'
        if bank in out['open_banks'] or not path.exists() or read(path).get('status')!='OPEN':continue
        a=read(path);require(a['bank']==bank and a['reservation_included'] is True and
            Decimal(str(a['allocation_usd']))==cap,'concrete original late-bank allocation')
        actual,unknown=bank_actual(SHARED/bank/'ledger');left=max(Decimal(0),Decimal(cap)-actual-unknown)
        out['open_banks'][bank]=dict(cap=str(cap),settled_usd=str(actual),physical_unknown_usd=str(unknown),open_usd=str(left))
        for k in ('open_caps_remaining_usd','actual_plus_open_caps_usd'):out[k]=str(Decimal(out[k])+left)
    total=Decimal(out['actual_plus_open_caps_usd']);require(total<=1000,'all evidenced current exposure<=1000')
    out['warning_triggered']=total>=800
    return out
