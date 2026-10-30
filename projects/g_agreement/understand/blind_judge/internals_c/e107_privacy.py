"""E107 judge copies under existing79f63fe0/25c32f25, not a wire exception.

Original descriptions/IDs/property/candidates/rubrics and no-schema-retry policy
are retained. Kept affected evidence must also be verbatim in original raw text.
"""
import argparse
from pathlib import Path
from . import registered
from .phase226 import run as phase_run
from .runner import CACHE
from .transport import ROOT, HERE
from .e109_privacy import raw_evidence_guard
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def copy_units(units):
    primary = [u['data'] for u in units if u['kind'] == 'value']
    copied, audit = redact(primary, 'E107', addresses=True)
    by = {x['id']: x for x in copied}
    affected = {x['id'] for x in audit['affected']}
    original = {x['id']: x['readout'] for x in primary if x['id'] in affected}
    result = []
    for unit in units:
        require(unit['kind'] in ('value', 'old_value') and unit['id'] in by, 'same complete primary/original scope')
        require(by[unit['id']]['property'] == unit['data']['property'] and
                by[unit['id']]['values'] == unit['data']['values'], 'property/candidate bytes unchanged')
        result.append(dict(unit, data=by[unit['id']]))
    return result, audit, original


def prepare():
    src = CACHE/'E107/outside_judge_units'
    verify(src/'UNIT_SEAL.json', sha(src/'UNIT_SEAL.json'))
    units, audit, original = copy_units(read(src/'UNITS.json'))
    dest = CACHE/'E107/outside_judge_privacy_copy_units'
    dest.mkdir(parents=True, exist_ok=True)
    dest.chmod(0o700)
    if (dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json', sha(dest/'UNIT_SEAL.json'))
        require(read(dest/'UNITS.json') == units, 'immutable E107 judge copies')
        return dest
    write(dest/'UNITS.json', units)
    write(dest/'PATH_REDACTION_AUDIT.json', audit)
    write(dest/'ORIGINAL_EVIDENCE.PRIVATE.json', original)
    custody = read(src/'CUSTODY.json')
    custody['source_seals'].append(dict(seal=str(src/'UNIT_SEAL.json'), sha256=sha(src/'UNIT_SEAL.json')))
    custody.update(path_redaction_authority='79f63fe0', redacted_records=audit['redacted_records'],
                   redaction_audit_sha256=sha(dest/'PATH_REDACTION_AUDIT.json'))
    write(dest/'CUSTODY.json', custody)
    write(dest/'UNIT_SEAL.json', dict(experiment='E107', n_primary=4496, n_original=1124,
        files={n: sha(dest/n) for n in ('UNITS.json', 'CUSTODY.json', 'PATH_REDACTION_AUDIT.json', 'ORIGINAL_EVIDENCE.PRIVATE.json')}))
    write(dest/'PREPARE_SPEC.json', dict(bank='E107', unit_seal=str(dest/'UNIT_SEAL.json'),
        unit_sha256=sha(dest/'UNIT_SEAL.json'), phase_name='outside_judge_copy'))
    return dest


def run(dest):
    for name, digest in read(HERE/'E107_PRIVACY_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name) == digest, 'published E107 privacy/source pin')
    s = verify(dest/'INPUT_SEAL.json', sha(dest/'INPUT_SEAL.json'))
    require(s['experiment'] == 'E107', 'E107 only')
    ref = s['source_seals'][0]
    verify(ref['seal'], ref['sha256'])
    unit_root = Path(ref['seal']).parent
    audit = read(unit_root/'PATH_REDACTION_AUDIT.json')
    original = read(unit_root/'ORIGINAL_EVIDENCE.PRIVATE.json')
    require(audit['authority'] == '79f63fe0' and audit['address_authority'] == '25c32f25' and audit['bank'] == 'E107' and
            set(original) == {x['id'] for x in audit['affected']}, 'full exact original evidence/audit binding')
    old_call, old_write = registered.unit_call, registered.write
    registered.unit_call = lambda unit, protocol: raw_evidence_guard(lambda u: old_call(u, protocol), unit, original)
    def audited_write(path, value):
        path = Path(path)
        if path.name == 'JUDGMENT_SEAL.json':
            ap = path.parent/'PATH_REDACTION_AUDIT.json'
            old_write(ap, audit)
            value = dict(value, redacted_records=audit['redacted_records'], redacted_opaque_ids=sorted(original),
                         redaction_authority='79f63fe0', address_redaction_authority='25c32f25', sensitivity_required=audit['sensitivity_required'],
                         files=dict(value['files'], **{'PATH_REDACTION_AUDIT.json': sha(ap)}))
        old_write(path, value)
    registered.write = audited_write
    try:
        return phase_run(dest)
    finally:
        registered.unit_call, registered.write = old_call, old_write


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run'))
    p.add_argument('--phase-directory', type=Path)
    args = p.parse_args()
    if args.action == 'prepare':
        dest = prepare()
        print('E107 judge-copy units '+sha(dest/'UNIT_SEAL.json'))
    else:
        run(args.phase_directory)
