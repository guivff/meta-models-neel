"""E109: existing79f63fe0 path redaction on judge copies, exact raw retained.

No privacy guard or frozen rubric is changed. Evidence in kept codes must also
occur verbatim in the original readout; the full affected-ID audit is present
before the first judgment seal is written. Analysis sensitivity belongs to owner.
"""
import argparse
from pathlib import Path
from . import registered
from .transport import ROOT
from .runner import CACHE
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def copy_units(units):
    primary=[u['data'] for u in units if u['kind']=='value']
    copied,audit=redact(primary,'E109',addresses=False)
    by={x['id']:x for x in copied}
    affected={x['id'] for x in audit['affected']}
    original={x['id']:x['readout'] for x in primary if x['id'] in affected}
    output=[]
    for u in units:
        require(u['kind'] in ('value','old_value') and u['id'] in by,'same frozen primary/original scope')
        changed=dict(u,data=by[u['id']])
        require(changed['data']['property']==u['data']['property'] and changed['data']['values']==u['data']['values'],'property/value bytes unchanged')
        output.append(changed)
    return output,audit,original


def prepare():
    src=CACHE/'E109/oracle_arrival_units'
    verify(src/'UNIT_SEAL.json',sha(src/'UNIT_SEAL.json'))
    units,audit,original=copy_units(read(src/'UNITS.json'))
    dest=CACHE/'E109/oracle_arrival_privacy_copy_units';dest.mkdir(parents=True,exist_ok=True);dest.chmod(0o700)
    if(dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json',sha(dest/'UNIT_SEAL.json'));require(read(dest/'UNITS.json')==units,'immutable judge copies')
        return dest
    write(dest/'UNITS.json',units);write(dest/'PATH_REDACTION_AUDIT.json',audit);write(dest/'ORIGINAL_EVIDENCE.PRIVATE.json',original)
    custody=read(src/'CUSTODY.json');custody['source_seals'].append(dict(seal=str(src/'UNIT_SEAL.json'),sha256=sha(src/'UNIT_SEAL.json')))
    custody.update(path_redaction_authority='79f63fe0',redaction_audit_sha256=sha(dest/'PATH_REDACTION_AUDIT.json'),redacted_records=audit['redacted_records'])
    write(dest/'CUSTODY.json',custody)
    write(dest/'UNIT_SEAL.json',dict(experiment='E109',n_primary=1008,n_original=252,files={n:sha(dest/n)for n in ('UNITS.json','CUSTODY.json','PATH_REDACTION_AUDIT.json','ORIGINAL_EVIDENCE.PRIVATE.json')}))
    write(dest/'PREPARE_SPEC.json',dict(bank='E109',unit_seal=str(dest/'UNIT_SEAL.json'),unit_sha256=sha(dest/'UNIT_SEAL.json'),phase_name='oracle_arrival_copy'))
    return dest


def raw_evidence_guard(base,unit,original):
    call,validator=base(unit)
    def checked(value):
        validator(value)
        if unit['id'] in original:
            require(value['records'][0]['evidence'] in original[unit['id']],'kept evidence must be verbatim in original raw source too')
    return call,checked


def run(dest):
    s=verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'));require(s['experiment']=='E109','E109 only')
    ref=s['source_seals'][0];verify(ref['seal'],ref['sha256']);units=Path(ref['seal']).parent
    audit=read(units/'PATH_REDACTION_AUDIT.json');original=read(units/'ORIGINAL_EVIDENCE.PRIVATE.json')
    require(audit['authority']=='79f63fe0' and set(original)=={x['id']for x in audit['affected']},'complete exact affected source binding')
    old_call=registered.unit_call;old_write=registered.write
    registered.unit_call=lambda unit,protocol:raw_evidence_guard(lambda u:old_call(u,protocol),unit,original)
    def audited_write(path,value):
        path=Path(path)
        if path.name=='JUDGMENT_SEAL.json':
            ap=path.parent/'PATH_REDACTION_AUDIT.json';old_write(ap,audit)
            value=dict(value,redacted_records=audit['redacted_records'],redacted_opaque_ids=sorted(original),
                redaction_authority='79f63fe0',sensitivity_required=audit['sensitivity_required'],
                files=dict(value['files'],PATH_REDACTION_AUDIT_json=sha(ap)))
            value['files'].pop('PATH_REDACTION_AUDIT_json');value['files']['PATH_REDACTION_AUDIT.json']=sha(ap)
        old_write(path,value)
    registered.write=audited_write
    try:return registered.run(dest)
    finally:registered.unit_call,registered.write=old_call,old_write


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run']);p.add_argument('--phase-directory',type=Path);a=p.parse_args()
    if a.action=='prepare':
        d=prepare();print('E109 judge-copy unit seal '+sha(d/'UNIT_SEAL.json'))
    else:run(a.phase_directory)
