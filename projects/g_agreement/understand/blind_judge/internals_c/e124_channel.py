"""Separate E124 model-answer judging; complete registered behaviour sources required."""
import argparse
import os
import subprocess
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from . import runner, transport
from .accounting233 import snapshot
from .banks import validate_schema
from .accounting import bank_actual
from .e124_amendment1_judge import calls_for
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

CAP = Decimal('3')
SOURCE = transport.HERE/'E124_SOURCE_SEAL.json'


def source_gate():
    transport.source_gate()
    for name, digest in read(SOURCE)['files'].items():
        require(sha(transport.ROOT/name) == digest, 'E124 prospective source pin')


def verify_unit_refs(units, custody, sources):
    require(custody['registered_behavior_references_verified'] is True and custody['complete_eligible_grid'] is True,
            'actual registered behaviour-measure/census verification under amendment1')
    pointers = {x['id']: x for x in custody['units']}
    require(len(pointers) == len(custody['units']) == len(units) and set(pointers) == {x['id'] for x in units},
            'complete exact CPU source crosswalk')
    files = {}
    for source in sources:
        verify(source['seal'], source['sha256'])
    def value(ref):
        source = sources[ref['seal_index']]
        seal_path = Path(source['seal'])
        sealed = read(seal_path)
        require(ref['member'] in sealed['files'], 'original sealed member')
        path = seal_path.parent/ref['member']
        require(sha(path) == sealed['files'][ref['member']], 'unchanged literal source member')
        if str(path) not in files: files[str(path)] = read(path)
        v = files[str(path)]
        for key in ref['keys']: v = v[key]
        return v
    for unit in units:
        pointer = pointers[unit['id']]
        require(value(pointer['model_reference_ref']) == unit['model_reference'] and
                value(pointer['readout_ref']) == unit['readout'], 'literal sealed registered reference/readout, no unbound replacement')


def prepare(owner_path, owner_sha):
    source_gate()
    require(read(SOURCE)['report_adapter_pinned'] is True, 'owner report source must be frozen before preparing paid phase')
    s = verify(owner_path, owner_sha)
    require(s['experiment'] == 'E124' and s['phase'] == 'model_reference_consistency' and
            s['frozen_before_judging'] is True and s['unit_definition_frozen'] is True and
            {'UNITS.json', 'CUSTODY.PRIVATE.json'} <= set(s['files']) and bool(s['source_seals']),
            'complete frozen owner science/unit/source packet required')
    units = read(owner_path.parent/'UNITS.json')
    custody = read(owner_path.parent/'CUSTODY.PRIVATE.json')
    verify_unit_refs(units, custody, s['source_seals'])
    calls = calls_for(units)
    require(len(calls) == s['n'], 'no subset of frozen owner census')
    dest = runner.seal_phase('E124', 'model_reference_consistency_judging', calls,
        dict(n=len(calls), owner_seal_sha256=owner_sha, E124_source_seal_sha256=sha(SOURCE),
             max_schema_retries=0, no_scientific_selection_by_transport=True),
        [dict(seal=str(owner_path), sha256=owner_sha)])
    return dest, runner.preflight(dest)


class E124Transport(transport.Transport):
    def __init__(self, path, digest, admission, key):
        require(admission['bank'] == 'E124' and Decimal(str(admission['allocation_usd'])) == CAP and
                admission['E124_source_seal_sha256'] == sha(SOURCE), 'separate lifetime3/source-bound E124')
        super().__init__(path, digest, admission, key)


@contextmanager
def worker():
    source_gate()
    prior = transport.CAPS.get('E124')
    require(prior in (None, CAP), 'separate E124 cap unchanged')
    transport.CAPS['E124'] = CAP
    try:
        yield
    finally:
        if prior is None:
            transport.CAPS.pop('E124', None)
        else:
            transport.CAPS['E124'] = prior


def acquire(dest, admission, channel_type, key):
    """Single attempt per unit; seal raw files by actual call phase, not directory."""
    job = dest/'outputs'
    job.mkdir(exist_ok=True)
    final = job/'JUDGMENT_SEAL.json'
    if final.exists():
        verify(final, sha(final))
        return final
    started = time.time()
    write(job/'STATUS.json', dict(status='RUNNING', bank='E124', phase='model_reference_consistency', pid=os.getpid(), start_epoch=started))
    terminals, audits, bindings = [], [], []
    try:
        with channel_type(dest/'INPUT_SEAL.json', sha(dest/'INPUT_SEAL.json'), admission, key) as channel:
            for call in channel.calls:
                schema = call['rendered']['schema']['schema']
                terminal, audit = channel.call(call['id'], lambda v, s=schema: validate_schema(v, s))
                require(terminal['id'] == call['id'], 'exact call/terminal identity')
                raw = channel.root/'ledger'/('E124_'+call['phase'])/(terminal['request_id']+'.response.json')
                require(sha(raw) == terminal['response_sha256'], 'exact physical raw response binding')
                terminals.append(terminal)
                audits.append(audit)
                bindings.append(dict(id=call['id'], phase=call['phase'], path=str(raw), sha256=sha(raw)))
                if len(terminals) == 1 or len(terminals) % 5 == 0:
                    write(job/'PROGRESS.json', dict(completed=len(terminals), n=len(channel.calls),
                        cost=channel.summary(), at_epoch=time.time()))
            require(len(terminals) == len(channel.calls), 'complete owner census')
            write(job/'RESPONSES.json', terminals)
            write(job/'ROUTE_AUDIT.json', dict(routes=channel.routes, requests=audits))
            write(job/'RAW_RESPONSE_BINDINGS.json', bindings)
            write(job/'COUNTS.json', dict(n=len(terminals), status_counts=dict(Counter(t['status'] for t in terminals)), cost=channel.summary()))
            write(job/'PROGRESS.json', dict(completed=len(terminals), n=len(channel.calls), cost=channel.summary(), at_epoch=time.time()))
            write(job/'STATUS.json', dict(status='COMPLETE', bank='E124', phase='model_reference_consistency', pid=os.getpid(), start_epoch=started, completed_epoch=time.time()))
            first = min(Path(b['path']).stat().st_mtime for b in bindings)
            write(final, dict(experiment='E124', phase='model_reference_consistency_judging', status='COMPLETE',
                first_output_utc=datetime.fromtimestamp(first, timezone.utc).isoformat(),
                first_output_source='earliest retained physical response file mtime',
                input_seal_sha256=sha(dest/'INPUT_SEAL.json'), source_seal_sha256=sha(transport.HERE/'SOURCE_SEAL.json'),
                E124_source_seal_sha256=sha(SOURCE), allocation_sha256=sha(dest/'ADMISSION.json'),
                route_verified=True, labels_cpu_only=True, redaction_audit_complete=True, redacted_records=0,
                files={p.name: sha(p) for p in job.iterdir() if p.is_file() and p != final}))
        return final
    except BaseException as exc:
        write(job/'STATUS.json', dict(status='PAUSED_402' if isinstance(exc, runner.funded.CreditPause) else 'STOPPED',
            bank='E124', phase='model_reference_consistency', error_type=type(exc).__name__, pid=os.getpid(), start_epoch=started))
        raise


def run(dest):
    source_gate()
    transport.unpaused()
    a = read(dest/'ADMISSION.json')
    require(a['input_sha256'] == sha(dest/'INPUT_SEAL.json') and a['E124_source_seal_sha256'] == sha(SOURCE), 'source/input admission')
    pub = read(dest/'PUBLICATION.json')
    path = Path(pub['allocation_path'])
    require(subprocess.check_output(['git', 'show', pub['commit']+':'+str(path.relative_to(transport.ROOT))], cwd=transport.ROOT) == path.read_bytes()
            and sha(path) == pub['allocation_sha256'] == sha(dest/'ADMISSION.json'), 'published immutable admission')
    proof = dest/'LIVE_PROOF.PRIVATE.json'
    require(sha(proof) == a['live_route_funding_proof_sha256'], 'published exact live proof')
    live = read(proof)
    require(0 <= time.time()-live['at_epoch'] < 300 and all(live[k] is True for k in
        ('route_verified', 'account_privacy_verified', 'funded_remaining_bank_cap')), 'fresh live route/privacy/funding')
    current = snapshot()
    require('E124' in current['open_banks'], 'separate canonical lifetime3 allocation must be OPEN')
    report = a['report_adapter_source']
    profile = read(SOURCE)
    require(profile['report_adapter_pinned'] is True and profile['files'].get(report['path']) == report['sha256'],
            'owner report receipt pinned in the prospective whole source manifest')
    report_path = transport.ROOT/report['path']
    committed_report = subprocess.check_output(['git', 'show', report['commit']+':'+report['path']], cwd=transport.ROOT)
    require(committed_report == report_path.read_bytes() and sha(report_path) == report['sha256'] and
            a['report_adapter_tests_verified'] is True and a['registered_behavior_measure_sources_verified'] is True,
            'published tested report adapter and exact registered behaviour-measure source verification before calls')
    actual, unknown = bank_actual(transport.SHARED/'E124/ledger')
    require(unknown == 0 and actual <= CAP, 'separate lifetime3 ledger, no unresolved charge')
    old = read(dest/'CPU_PREFLIGHT.json')
    require(runner.preflight(dest) == old, 'unchanged whole-source/full-wire privacy inventory')
    write(dest/'DISPATCH_GLOBAL_PROOF.PRIVATE.json', current)
    key = os.environ.get('OPENROUTER_API_KEY')
    require(bool(key), 'credential unavailable')
    with worker():
        return acquire(dest, a, E124Transport, key)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run'))
    p.add_argument('--owner-seal', type=Path)
    p.add_argument('--owner-sha256')
    p.add_argument('--phase-directory', type=Path)
    a = p.parse_args()
    if a.action == 'prepare':
        print(prepare(a.owner_seal, a.owner_sha256))
    else:
        run(a.phase_directory)
