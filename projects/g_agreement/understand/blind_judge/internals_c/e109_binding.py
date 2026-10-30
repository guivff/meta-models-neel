"""Exact CPU Oracle-code pointers and explicit original-schema missing sentinels.

No probe/statistic is computed. Kept codes point directly at the unchanged
JUDGMENTS.json[index].code. Non-kept nulls get the existing core.score missing
sentinel in a separate sealed file; the original null and status remain bound.
"""
import argparse
import hashlib
from pathlib import Path

from .transport import ROOT, HERE
from .runner import CACHE
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def code_refs(judgments, expected, source_index, scope, sentinels):
    by = {x['id']: (i, x) for i, x in enumerate(judgments)}
    require(len(by) == len(judgments) and set(by) == set(expected), 'complete unique original code census')
    result = {}
    for ident, (i, terminal) in by.items():
        require(terminal['kind'] == ('value' if scope == 'primary' else 'old_value') and
                terminal['status'] in ('KEPT', 'UNPARSEABLE', 'REFUSED'), 'known original terminal kind/status')
        if terminal['status'] == 'KEPT':
            require(isinstance(terminal['code'], dict) and terminal['code']['id'] == ident,
                    'original kept object and opaque identity')
            result[ident] = dict(seal_index=source_index, member='JUDGMENTS.json', keys=[i, 'code'])
        else:
            require(terminal['code'] is None, 'failed original code remains null')
            index = len(sentinels)
            sentinels.append(dict(id=ident, scope=scope, terminal_status=terminal['status'],
                original_code=dict(seal_index=source_index, member='JUDGMENTS.json', keys=[i, 'code']),
                code=dict(id=ident, category='UNPARSEABLE', values=[], evidence='')))
            result[ident] = dict(seal_index=2, member='MISSING_SENTINELS.PRIVATE.json', keys=[index, 'code'])
    return result


def resolve_redaction(audit, joins, read_text):
    by = {x['id']: x for x in joins}
    require(len(by) == len(joins), 'unique source crosswalk')
    require(audit['authority'] == '79f63fe0' and audit['redacted_records'] == len(audit['affected']),
            'complete original privacy audit')
    affected = []
    for entry in audit['affected']:
        require(entry['id'] in by, 'every affected opaque ID has original source mapping')
        join = by[entry['id']]
        require(hashlib.sha256(read_text(join).encode()).hexdigest() == entry['original_readout_sha256'],
                'original native text preserved verbatim')
        affected.append({k: join[k] for k in ('row', 'layer', 'condition', 'item_id')})
    return dict(all_affected_mapped=True, original_text_preserved=True, affected_readouts=affected)


def prepare():
    manifest = HERE/'E109_BINDING_SOURCE_SEAL.json'
    for name, digest in read(manifest)['files'].items():
        require(sha(ROOT/name) == digest, 'published CPU binding source pin')
    home = CACHE/'E109'
    unit_path = home/'oracle_arrival_units/UNIT_SEAL.json'
    verify(unit_path, sha(unit_path))
    unit_root = unit_path.parent
    custody = read(unit_root/'CUSTODY.json')
    native = custody['source_seals'][0]
    native_seal = verify(native['seal'], native['sha256'])
    require(native_seal['status'] == 'COMPLETE', 'complete original native source')
    primary = home/'oracle_arrival_copy_judging/outputs/JUDGMENT_SEAL.json'
    original = home/'oracle_arrival_copy_original/outputs/JUDGMENT_SEAL.json'
    for path in (primary, original):
        seal = verify(path, sha(path))
        require(seal['experiment'] == 'E109' and seal['status'] == 'COMPLETE' and
                seal['route_verified'] is True, 'both complete original judging phases')
    units = read(unit_root/'UNITS.json')
    joins = read(unit_root/'SOURCE_POINTERS.PRIVATE.json')
    primary_ids = [x['id'] for x in units if x['kind'] == 'value']
    original_ids = [x['id'] for x in units if x['kind'] == 'old_value']
    require(len(primary_ids) == len(joins) == 1008 and len(original_ids) == 252 and
            set(primary_ids) == {x['id'] for x in joins}, 'original1008+seeded252 census')
    sentinels = []
    main_refs = code_refs(read(primary.parent/'JUDGMENTS.json'), primary_ids, 1, 'primary', sentinels)
    old_refs = code_refs(read(original.parent/'JUDGMENTS.json'), original_ids, 3, 'original', sentinels)
    records = []
    for join in joins:
        ref = join['source_ref']
        require(ref['member'] in native_seal['files'], 'unchanged native readout member')
        records.append(dict({k: join[k] for k in ('id', 'row', 'item_id', 'condition', 'layer')},
            text=dict(seal_index=0, member=ref['member'], keys=[ref['index'], 'text']),
            code=main_refs[join['id']], original_code=old_refs.get(join['id'])))
    audit = read(primary.parent/'PATH_REDACTION_AUDIT.json')
    def native_text(join):
        ref = join['source_ref']
        return read(Path(native['seal']).parent/ref['member'])[ref['index']]['text']
    resolved = resolve_redaction(audit, joins, native_text)
    dest = home/'oracle_code_binding'
    dest.mkdir(exist_ok=True)
    dest.chmod(0o700)
    if (dest/'BINDING_SEAL.json').exists():
        prior = verify(dest/'BINDING_SEAL.json', sha(dest/'BINDING_SEAL.json'))
        require(prior['primary_sha256'] == sha(primary) and prior['original_sha256'] == sha(original),
                'immutable complete binding')
        return dest
    write(dest/'ORACLE_POINTERS.PRIVATE.json', records)
    write(dest/'MISSING_SENTINELS.PRIVATE.json', sentinels)
    write(dest/'REDACTION_RESOLVED.PRIVATE.json', resolved)
    write(dest/'NORMALIZATION_RECEIPT.json', dict(experiment='E109', source_manifest_sha256=sha(manifest),
        primary_sha256=sha(primary), original_sha256=sha(original), native_sha256=native['sha256'],
        original_crosswalk_sha256=sha(unit_root/'SOURCE_POINTERS.PRIVATE.json'),
        n_primary=1008, n_original=252, terminal_missing_sentinels=len(sentinels),
        kept_code_policy='direct JUDGMENTS.json[index].code, unchanged',
        missing_policy='original-schema UNPARSEABLE/empty-values/empty-evidence; original status/null pointer retained',
        redacted_readout_count=len(resolved['affected_readouts']), analysis_run=False))
    files = {p.name: sha(p) for p in dest.iterdir() if p.is_file() and p.name != 'BINDING_SEAL.json'}
    write(dest/'BINDING_SEAL.json', dict(experiment='E109', status='COMPLETE_CPU_BINDING',
        primary_sha256=sha(primary), original_sha256=sha(original), files=files))
    sources = [native, dict(seal=str(primary), sha256=sha(primary)),
               dict(seal=str(dest/'BINDING_SEAL.json'), sha256=sha(dest/'BINDING_SEAL.json')),
               dict(seal=str(original), sha256=sha(original)), dict(seal=str(unit_path), sha256=sha(unit_path))]
    write(dest/'HANDOFF_SPEC.PRIVATE.json', dict(source_seals=sources,
        oracle_pointers=dict(seal_index=2, member='ORACLE_POINTERS.PRIVATE.json', keys=[]),
        redaction_audit=dict(seal_index=2, member='REDACTION_RESOLVED.PRIVATE.json', keys=[]),
        redacted_readout_count=len(resolved['affected_readouts']),
        capture_bindings='Integrator original capture/dev/test source binding still required',
        analysis_run=False))
    return dest


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    dest = prepare()
    print('E109 complete Oracle-code CPU binding '+sha(dest/'BINDING_SEAL.json'))
