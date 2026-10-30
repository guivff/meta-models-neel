"""Complete prior exposure plus the separate live owner E79B reader bank."""
from decimal import Decimal
from .accounting236 import snapshot as previous
from .accounting import bank_actual
from .transport import SHARED
from projects.g_agreement.readerbench.io import read,sha,verify
from projects.g_agreement.readerbench.scoring import require


def add_e79b(out):
    root=SHARED/'E79_ARM_B';ap=root/'ADMISSION.json';state=root/'STATUS.json'
    if 'E79_ARM_B' in out['open_banks'] or not ap.exists() or not state.exists():return out
    a=read(ap);require(a['bank']=='E79_ARM_B' and Decimal(str(a['cap_usd']))==3 and a['records']==672 and a['cap_binding_sha256']=='fa1911a10694734d45b127d50a043b158e3cb8a887eb1bf77c974222cd80739f','actual original separately capped reader bank')
    actual,unknown=bank_actual(root/'ledger');terminal=root/'judgments/JUDGMENT_SEAL.json'
    if terminal.exists():
        s=verify(terminal,sha(terminal));require(s['bank']=='E79_ARM_B' and s['route_verified'] is True and s['cap_binding_sha256']==a['cap_binding_sha256'] and unknown==0,'owner completed bank verified before unused release')
        return out
    left=max(Decimal(0),Decimal(3)-actual-unknown)
    out['open_banks']['E79_ARM_B']=dict(cap='3',settled_usd=str(actual),physical_unknown_usd=str(unknown),open_usd=str(left),admission_sha256=sha(ap))
    for k in ('open_caps_remaining_usd','actual_plus_open_caps_usd'):out[k]=str(Decimal(out[k])+left)
    require(Decimal(out['actual_plus_open_caps_usd'])<=1000,'complete all-bank exposure <=1000')
    return out


def snapshot(new_banks=()):return add_e79b(previous(new_banks))
