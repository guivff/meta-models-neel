"""Include the now OPEN W-judge95 lifetime allocation in prospective C proofs."""
from decimal import Decimal
from pathlib import Path
from .accounting138r254 import snapshot as previous
from .accounting import bank_actual
from .transport import SHARED
from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require

def add_e95(out,root=SHARED/'E95'):
    p=root/'ALLOCATION_WJ95.json'
    if not p.exists():return out
    a=read(p)
    if a['status']!='OPEN':
        require(a['status']=='RELEASED','known E95 allocation disposition');return out
    require(a['experiment']=='E95' and a['operator']=='W-judge95' and a['reservation_included']is True and Decimal(a['allocation_usd'])==Decimal(a['lifetime_maximum_usd'])==60 and a['per_stage_reset']is False,'actual original E95 lifetime60, not stage reset')
    ledger=Path(a['ledger_root']);require(ledger.resolve().is_relative_to(root.resolve()),'exact canonical E95 ledger custody')
    if 'E95'in out['open_banks']:
        require(Decimal(out['open_banks']['E95']['cap'])==60,'same lifetime E95 cap, no duplicate');return out
    actual,unknown=bank_actual(ledger);left=max(Decimal(0),Decimal(60)-actual-unknown)
    out['open_banks']['E95']=dict(cap='60',settled_usd=str(actual),physical_unknown_usd=str(unknown),open_usd=str(left),allocation_sha256=sha(p),ledger_root=str(ledger),operator='W-judge95')
    for k in ['open_caps_remaining_usd','actual_plus_open_caps_usd']:out[k]=str(Decimal(out[k])+left)
    require(Decimal(out['actual_plus_open_caps_usd'])<=1000,'all-bank limit including E95');out['warning_triggered']=Decimal(out['actual_plus_open_caps_usd'])>=800;return out

def snapshot(new_banks=()):return add_e95(previous(new_banks))
