"""Prospective complete census of actual OPEN C allocations; queued caps excluded."""
from decimal import Decimal
from .accounting_e79b import snapshot as previous
from .accounting import bank_actual
from .transport import SHARED
from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require
KNOWN={'E107b':Decimal(2),'E118':Decimal(1),'E133':Decimal(5),'E135':Decimal(1),'E136':Decimal(1),'E137':Decimal(2),'E138':Decimal(1)}


def add_census(out,root=SHARED):
    proofs=[]
    for p in root.glob('*/ALLOCATION_C.json'):
        a=read(p)
        if a.get('status')!='OPEN':continue
        bank=p.parent.name;cap=Decimal(str(a['allocation_usd']));proofs.append(dict(bank=bank,allocation_sha256=sha(p),cap_usd=str(cap)))
        require(a['bank']==bank and a['operator']=='W-internals-C'and a['reservation_included']is True,'actual canonical C allocation')
        if bank in out['open_banks']:
            require(Decimal(out['open_banks'][bank]['cap'])==cap,'registered accounting cap agrees');continue
        require(bank in KNOWN and cap==KNOWN[bank],'unknown newly open bank must be registered before admission')
        actual,unknown=bank_actual(p.parent/'ledger');left=max(Decimal(0),cap-actual-unknown)
        out['open_banks'][bank]=dict(cap=str(cap),settled_usd=str(actual),physical_unknown_usd=str(unknown),open_usd=str(left))
        for k in ['open_caps_remaining_usd','actual_plus_open_caps_usd']:out[k]=str(Decimal(out[k])+left)
    out['actual_C_allocation_census']=proofs;total=Decimal(out['actual_plus_open_caps_usd']);require(total<=1000,'all actual open banks and liabilities <=1000');out['warning_triggered']=total>=800;return out


def snapshot(new_banks=()):return add_census(previous(new_banks))
