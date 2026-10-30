"""Prospective §226 supplement; existing executing accounting pins stay intact."""
from decimal import Decimal
from .accounting_overlay import snapshot as prior_snapshot
from .accounting import bank_actual
from .transport import SHARED
from projects.g_agreement.readerbench.io import read
from projects.g_agreement.readerbench.scoring import require


def add_open_226(out):
    for bank, cap in {'E100e': 3, 'E114': 2}.items():
        path = SHARED/bank/'ALLOCATION_C.json'
        if not path.exists() or read(path).get('status') != 'OPEN' or bank in out['open_banks']:
            continue
        allocation = read(path)
        require(allocation['bank'] == bank and allocation['operator'] == 'W-internals-C' and
                allocation['reservation_included'] is True and Decimal(str(allocation['allocation_usd'])) == cap,
                'separate concrete section226 allocation')
        actual, unknown = bank_actual(SHARED/bank/'ledger')
        remaining = max(Decimal(0), Decimal(cap)-actual-unknown)
        out['open_banks'][bank] = dict(cap=str(cap), settled_usd=str(actual),
            physical_unknown_usd=str(unknown), open_usd=str(remaining))
        for key in ('open_caps_remaining_usd', 'actual_plus_open_caps_usd'):
            out[key] = str(Decimal(out[key])+remaining)
    total = Decimal(out['actual_plus_open_caps_usd'])
    require(total <= 1000, 'complete current actual plus all evidenced open caps and unknown holds')
    out['warning_triggered'] = total >= 800
    return out


def snapshot(new_banks=()):
    return add_open_226(prior_snapshot(new_banks))
