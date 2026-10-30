"""Prospective sole-C E123 allocation, inheriting every prior bank/physical hold."""
from decimal import Decimal
from .accounting233 import snapshot as previous
from .accounting import bank_actual
from .transport import SHARED
from projects.g_agreement.readerbench.io import read
from projects.g_agreement.readerbench.scoring import require


def add_open_234(out):
    path = SHARED/'E123/ALLOCATION_C.json'
    if 'E123' not in out['open_banks'] and path.exists() and read(path).get('status') == 'OPEN':
        a = read(path)
        require(a['bank'] == 'E123' and a['operator'] == 'W-internals-C' and
                a['reservation_included'] is True and Decimal(str(a['allocation_usd'])) == 3,
                'concrete sole-C E123 separate lifetime3 allocation')
        actual, unknown = bank_actual(SHARED/'E123/ledger')
        left = max(Decimal(0), Decimal(3)-actual-unknown)
        out['open_banks']['E123'] = dict(cap='3', settled_usd=str(actual), physical_unknown_usd=str(unknown), open_usd=str(left))
        for key in ('open_caps_remaining_usd', 'actual_plus_open_caps_usd'):
            out[key] = str(Decimal(out[key])+left)
    total = Decimal(out['actual_plus_open_caps_usd'])
    require(total <= 1000, 'all evidenced exposure <=1000')
    out['warning_triggered'] = total >= 800
    return out


def snapshot(new_banks=()):
    return add_open_234(previous(new_banks))
