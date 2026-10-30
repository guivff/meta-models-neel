"""Integrator-sealed preflight ceilings and USD100 cross-bank running guard."""
import re
from contextlib import contextmanager
from decimal import Decimal,ROUND_CEILING
from pathlib import Path

from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require
from .dispatch_lock import dispatch_lock
from .run import CACHE

BANKS={f'E{i}' for i in range(76,93)}


def cap_entry(spec,bank,observed_bound=None):
    require(bank in BANKS,'registered later bank')
    require(sha(spec['caps_seal'])==spec['caps_seal_sha256'],'caps seal pinned by run spec')
    seal=read(spec['caps_seal']);path=Path(spec['caps_file'])
    require(seal.get('issuer')=='integrator' and seal.get('verified') is True and
            path.name=='CAPS.json' and path.parent.resolve()==Path(spec['caps_seal']).parent.resolve() and
            sha(path)==seal['files']['CAPS.json'],'integrator-sealed caps file')
    cfg=read(path);require(cfg.get('authority')=='§200 0567e8a1' and
                           cfg.get('global_actual_and_unresolved_usd')==100 and
                           cfg.get('preflight_status')=='COMPLETE','§200 running envelope')
    c=cfg['banks'][bank];bound=Decimal(str(c['worst_case_first_pass_usd']))
    cap=Decimal(str(c['ceiling_usd']));expected=Decimal(str(c['expected_spend_usd']))
    require(all(x.is_finite() and x>=0 for x in (bound,cap,expected)) and
            cap==bound.to_integral_value(rounding=ROUND_CEILING) and
            c.get('expected_near_registration_verified') is True and
            c.get('integrator_preflight_verified') is True and
            cfg.get('daily_ceiling_usd')==300,
            'ceiling is integrator worst-case initial bound rounded up')
    if observed_bound is not None:
        require(abs(bound-Decimal(str(observed_bound)))<=Decimal('.00000001'),
                'live packet bound differs from sealed preflight')
    return cap


def running_total(api):
    total=Decimal(0)
    for path in CACHE.iterdir() if CACHE.exists() else []:
        if path.is_dir() and path.name!='e81_e86_17usd' and re.match(r'e(?:7[6-9]|8\d|9[0-2])(?:_|$)',path.name):
            ledger=path/'ledger.jsonl'
            if ledger.exists():
                book,_=api.Ledger(ledger).totals()
                total+=sum(book.values(),Decimal(0))
    return total


@contextmanager
def global_send(api,wire):
    """One request holds the shared lock through settlement, accounting for unresolved sends."""
    with dispatch_lock(CACHE/'e76_e88_GLOBAL.lock'):
        require(running_total(api)+api.upper(wire)<=Decimal('100'),
                'E76–E88 USD100 global running total before send')
        yield
