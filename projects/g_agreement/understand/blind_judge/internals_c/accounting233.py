"""E124's separate concrete OPEN allocation; all prior exposure stays included."""
from decimal import Decimal
from .accounting231 import snapshot as previous
from .accounting import bank_actual
from .transport import SHARED
from projects.g_agreement.readerbench.io import read
from projects.g_agreement.readerbench.scoring import require


def add_open_233(out):
    path = SHARED/'E124/ALLOCATION_C.json'
    if 'E124' not in out['open_banks'] and path.exists() and read(path).get('status') == 'OPEN':
        a = read(path)
        require(a['bank'] == 'E124' and a['operator'] == 'W-internals-C' and
                a['reservation_included'] is True and Decimal(str(a['allocation_usd'])) == 3,
                'separate concrete E124 lifetime3 allocation')
        actual, unknown = bank_actual(SHARED/'E124/ledger')
        left = max(Decimal(0), Decimal(3)-actual-unknown)
        out['open_banks']['E124'] = dict(cap='3', settled_usd=str(actual), physical_unknown_usd=str(unknown), open_usd=str(left))
        for key in ('open_caps_remaining_usd', 'actual_plus_open_caps_usd'):
            out[key] = str(Decimal(out[key])+left)
    total = Decimal(out['actual_plus_open_caps_usd'])
    require(total <= 1000, 'all evidenced exposure <=1000')
    out['warning_triggered'] = total >= 800
    return out


def snapshot(new_banks=()):
    return add_open_233(previous(new_banks))
