"""Isolated E85 registered worker with original-raw evidence and privacy audit."""
import argparse
from pathlib import Path
from contextlib import contextmanager
from . import registered
from .transport import ROOT,HERE
from .phase226 import run as phase_run
from projects.g_agreement.readerbench.io import read,sha,write,verify
from projects.g_agreement.readerbench.scoring import require


@contextmanager
def worker(dest=None):
    for name,digest in read(HERE/'E85_RUNTIME_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/name)==digest,'E85 exact source pin')
    old_here=registered.HERE;registered.HERE=HERE/'E85'
    old_call,old_write=registered.unit_call,registered.write
    if dest is not None:
        sealed=verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'));source=sealed['source_seals'][0];verify(source['seal'],source['sha256'])
        units=Path(source['seal']).parent;audit=read(units/'PATH_REDACTION_AUDIT.json');original=read(units/'ORIGINAL_EVIDENCE.PRIVATE.json')
        def call(unit,protocol):
            result,base=old_call(unit,protocol)
            def validate(value):
                base(value)
                if unit['id'] in original:
                    spans=[value[k] for k in ('a_evidence','b_evidence','c_evidence')] if unit['kind']=='eval85' else [value['records'][0]['evidence']]
                    require(all(s in original[unit['id']] for s in spans),'evidence verbatim in unchanged original raw too')
            return result,validate
        registered.unit_call=call
        def audited(path,value):
            path=Path(path)
            if path.name=='JUDGMENT_SEAL.json':
                ap=path.parent/'PATH_REDACTION_AUDIT.json';old_write(ap,audit)
                value=dict(value,redacted_records=audit['redacted_records'],redacted_opaque_ids=sorted(original),
                    files=dict(value['files'],**{'PATH_REDACTION_AUDIT.json':sha(ap)}),sensitivity_required=audit['sensitivity_required'])
            old_write(path,value)
        registered.write=audited
    try:yield
    finally:registered.HERE=old_here;registered.unit_call,registered.write=old_call,old_write


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'));p.add_argument('--spec',type=Path);p.add_argument('--phase-directory',type=Path);a=p.parse_args()
    with worker(a.phase_directory if a.action=='run' else None):
        if a.action=='prepare':registered.prepare(a.spec)
        else:phase_run(a.phase_directory)
