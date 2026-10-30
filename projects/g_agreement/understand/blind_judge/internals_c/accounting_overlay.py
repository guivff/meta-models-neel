"""Prospective supplement for the newly active E99 phase1 allocation.

The canonical ledger retains its historical40usd directory name. Its active
allocation is150, read from I-2's posted start receipt, with physical costs/holds
already included in the base census. Completed phase1 releases the open cap;
conditional400 is never allocated by this code.
"""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from .accounting import snapshot as base_snapshot,bank_actual
from .transport import ROOT,SHARED
from projects.g_agreement.readerbench.io import read,sha,verify
from projects.g_agreement.readerbench.scoring import require


def supplement(base,cap,actual,unknown,active):
    out=deepcopy(base);cap=Decimal(str(cap));actual=Decimal(str(actual));unknown=Decimal(str(unknown))
    require(cap==150 and actual>=0 and unknown>=0,'registered E99 phase1 values')
    previous=Decimal(out['open_banks'].get('E99_phase1',{}).get('open_usd','0'))
    remaining=max(Decimal(0),cap-actual-unknown) if active else Decimal(0)
    out['open_banks']['E99_phase1']=dict(cap=str(cap),settled_usd=str(actual),physical_unknown_usd=str(unknown),open_usd=str(remaining),active=active)
    out['open_caps_remaining_usd']=str(Decimal(out['open_caps_remaining_usd'])-previous+remaining)
    total=Decimal(out['actual_plus_open_caps_usd'])-previous+remaining
    require(total<=1000,'complete current global exposure ceiling')
    out['actual_plus_open_caps_usd']=str(total);out['warning_triggered']=total>=800
    return out


def snapshot(new_banks=()):
    base=base_snapshot(new_banks)
    receipt=ROOT.parent/'wt-i2/results/g_agreement/i2/E99_PHASE1_STARTED_SECTION221.json'
    if not receipt.exists():receipt=ROOT/'results/g_agreement/i2/E99_PHASE1_STARTED_SECTION221.json'
    require(receipt.exists(),'new active E99 owner receipt must be present')
    source=read(receipt);require(source['experiment']=='E99' and Decimal(str(source['allocation_usd']))==150 and
        source['continuation_to400_not_allocated'] is True,'explicit phase1 allocation, no conditional400 inference')
    root=Path(source['canonical_ledger_root']);require((root/'ledger.jsonl').exists() and (root/'phase1_section221/START.json').exists(),'actual original E99 ledger/start source')
    a,u=bank_actual(root);terminal=root/'phase1_section221/RESULT_SEAL.json'
    active=not terminal.exists()
    if not active:verify(terminal,sha(terminal))
    out=supplement(base,source['allocation_usd'],a,u,active)
    out['E99_owner_start_receipt_sha256']=sha(receipt)
    out['E99_conditional400_allocated']=False
    return add_concrete_extras(out)


def add_concrete_extras(out):
    # New C banks live in independently posted concrete allocations; queued
    # authorizations without an OPEN receipt never count as running caps.
    for bank,cap in {'E112':3,'E84':3,'E110':10}.items():
        allocation=SHARED/bank/'ALLOCATION_C.json'
        if not allocation.exists() or read(allocation).get('status')!='OPEN' or bank in out['open_banks']:continue
        a=read(allocation)
        require(a['bank']==bank and a['operator']=='W-internals-C' and a['reservation_included'] is True and
            Decimal(str(a['allocation_usd']))==cap,'posted separate registered extra bank cap')
        actual,unknown=bank_actual(SHARED/bank/'ledger');remaining=max(Decimal(0),Decimal(cap)-actual-unknown)
        out['open_banks'][bank]=dict(cap=str(cap),settled_usd=str(actual),physical_unknown_usd=str(unknown),open_usd=str(remaining))
        out['open_caps_remaining_usd']=str(Decimal(out['open_caps_remaining_usd'])+remaining)
        out['actual_plus_open_caps_usd']=str(Decimal(out['actual_plus_open_caps_usd'])+remaining)
    require(Decimal(out['actual_plus_open_caps_usd'])<=1000,'complete active-bank ceiling')
    out['warning_triggered']=Decimal(out['actual_plus_open_caps_usd'])>=800
    return out
