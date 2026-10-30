"""Prospective E120/E121 concrete allocations, inheriting all prior exposure."""
from decimal import Decimal
from .accounting229 import snapshot as previous
from .accounting import bank_actual
from .transport import SHARED
from projects.g_agreement.readerbench.io import read
from projects.g_agreement.readerbench.scoring import require


def add_open_231(out):
    for bank, cap in {'E120': 2, 'E121': 1}.items():
        path = SHARED/bank/'ALLOCATION_C.json'
        if bank in out['open_banks'] or not path.exists() or read(path).get('status') != 'OPEN':
            continue
        a = read(path)
        require(a['bank'] == bank and a['operator'] == 'W-internals-C' and
                a['reservation_included'] is True and Decimal(str(a['allocation_usd'])) == cap,
                'separate concrete section231 lifetime allocation')
        actual, unknown = bank_actual(SHARED/bank/'ledger')
        left = max(Decimal(0), Decimal(cap)-actual-unknown)
        out['open_banks'][bank] = dict(cap=str(cap), settled_usd=str(actual),
            physical_unknown_usd=str(unknown), open_usd=str(left))
        for k in ('open_caps_remaining_usd', 'actual_plus_open_caps_usd'):
            out[k] = str(Decimal(out[k])+left)
    total = Decimal(out['actual_plus_open_caps_usd'])
    require(total <= 1000, 'all evidenced exposure <=1000')
    out['warning_triggered'] = total >= 800
    return out


def snapshot(new_banks=()):
    return add_open_231(previous(new_banks))
