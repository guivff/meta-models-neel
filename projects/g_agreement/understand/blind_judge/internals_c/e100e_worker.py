"""Separate E100e3 process, exact E82/value and seeded original comparison."""
import argparse
from collections import Counter
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from . import registered,transport
from .accounting226 import snapshot
from .e109_privacy import raw_evidence_guard
from ..rubric202 import original_ids
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def check_scope(bank,units,c):
    require(bank=='E100e' and c.get('experiment')==bank and c.get('verified')is True and
        c.get('complete_eligible_native_grid')is True and c.get('labels_cpu_only')is True,'complete E100e owner grid')
    require(Counter(x['kind']for x in units)=={'value':336,'old_value':84},'all336 plus registered202 original25%')
    main=[x['id']for x in units if x['kind']=='value'];old=sorted(x['id']for x in units if x['kind']=='old_value')
    require(old==original_ids(main,'E100e'),'exact original seeded25% comparison')


@contextmanager
def worker(dest=None):
    for name,digest in read(transport.HERE/'E100e_RUNTIME_SOURCE_SEAL.json')['files'].items():require(sha(transport.ROOT/name)==digest,'E100e runtime source pin')
    prior=transport.CAPS.get('E100e');require(prior in (None,Decimal(3)),'separate E100e cap3');transport.CAPS['E100e']=Decimal(3)
    saved={n:getattr(registered,n)for n in ('HERE','check_scope','snapshot','unit_call','write')}
    registered.HERE=transport.HERE/'E100e';registered.check_scope=check_scope;registered.snapshot=snapshot
    if dest is not None:
        s=verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'));ref=s['source_seals'][0];verify(ref['seal'],ref['sha256']);src=Path(ref['seal']).parent
        original=read(src/'ORIGINAL_EVIDENCE.PRIVATE.json');audit=read(src/'PATH_REDACTION_AUDIT.json')
        registered.unit_call=lambda unit,p:raw_evidence_guard(lambda u:saved['unit_call'](u,p),unit,original)
        def audited(path,value):
            path=Path(path)
            if path.name=='JUDGMENT_SEAL.json':
                ap=path.parent/'PATH_REDACTION_AUDIT.json';saved['write'](ap,audit)
                value=dict(value,redacted_records=audit['redacted_records'],redacted_opaque_ids=sorted(original),
                    files=dict(value['files'],**{'PATH_REDACTION_AUDIT.json':sha(ap)}),sensitivity_required=audit['sensitivity_required'])
            saved['write'](path,value)
        registered.write=audited
    try:yield
    finally:
        for name,value in saved.items():setattr(registered,name,value)
        if prior is None:transport.CAPS.pop('E100e',None)
        else:transport.CAPS['E100e']=prior


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'));p.add_argument('--spec',type=Path);p.add_argument('--phase-directory',type=Path);a=p.parse_args()
    with worker(a.phase_directory if a.action=='run'else None):
        if a.action=='prepare':registered.prepare(a.spec)
        else:registered.run(a.phase_directory)
