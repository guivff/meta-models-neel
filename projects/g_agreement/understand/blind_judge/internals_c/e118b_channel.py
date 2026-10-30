"""Transport only for owner-frozen E118b units; no scientific unit selection."""
import argparse
import json
import os
import re
import subprocess
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from . import runner, transport
from .accounting231 import snapshot
from .banks import object_schema, validate_schema
from .accounting import bank_actual
from projects.g_agreement.e118_analysis.adapter import SYSTEM
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

CAP = Decimal('1')
SOURCE = transport.HERE/'E118B_SOURCE_SEAL.json'


def source_gate():
    transport.source_gate()
    for name, digest in read(SOURCE)['files'].items():
        require(sha(transport.ROOT/name) == digest, 'E118b prospective source pin')


def calls_for(units):
    require(bool(units) and len({x['id'] for x in units}) == len(units), 'complete unique owner units')
    calls = []
    for x in units:
        require(set(x) == {'id', 'context', 'readout'} and
                re.fullmatch(r'[0-9a-f]{20,64}', x['id']) is not None and
                type(x['context']) is str and bool(x['context']) and type(x['readout']) is str,
                'only opaque ID and literal source context/readout on wire')
        calls.append(dict(id=x['id'], phase='judging', rendered=dict(system=SYSTEM,
            user=json.dumps(x, ensure_ascii=False),
            schema=object_schema('context_consistency', {'verdict': {'type': 'string',
                'enum': ['YES', 'NO', 'OFF-TOPIC']}}))))
    return sorted(calls, key=lambda c: c['id'])


def prepare(owner_path, owner_sha):
    source_gate()
    s = verify(owner_path, owner_sha)
    require(s['experiment'] == 'E118' and s['phase'] == 'part_b' and
            s['frozen_before_judging'] is True and s['unit_definition_frozen'] is True and
            {'UNITS.json', 'CUSTODY.PRIVATE.json'} <= set(s['files']) and bool(s['source_seals']),
            'complete frozen owner science/unit/source packet required')
    for ref in s['source_seals']:
        verify(ref['seal'], ref['sha256'])
    calls = calls_for(read(owner_path.parent/'UNITS.json'))
    require(len(calls) == s['n'], 'no subset of frozen owner census')
    dest = runner.seal_phase('E118', 'belief_wrong_consistency_judging', calls,
        dict(n=len(calls), owner_seal_sha256=owner_sha, E118b_source_seal_sha256=sha(SOURCE),
             max_schema_retries=0, no_scientific_selection_by_transport=True),
        [dict(seal=str(owner_path), sha256=owner_sha)])
    return dest, runner.preflight(dest)


class E118bTransport(transport.Transport):
    def __init__(self, path, digest, admission, key):
        require(admission['bank'] == 'E118' and Decimal(str(admission['allocation_usd'])) == CAP and
                admission['E118b_source_seal_sha256'] == sha(SOURCE), 'same lifetime1/source-bound E118b')
        super().__init__(path, digest, admission, key)


@contextmanager
def worker():
    source_gate()
    prior = transport.CAPS.get('E118')
    require(prior in (None, CAP), 'no bank cap reset')
    transport.CAPS['E118'] = CAP
    try:
        yield
    finally:
        if prior is None:
            transport.CAPS.pop('E118', None)
        else:
            transport.CAPS['E118'] = prior


def acquire(dest, admission, channel_type, key):
    """Single attempt per unit; seal raw files by actual call phase, not directory."""
    job = dest/'outputs'
    job.mkdir(exist_ok=True)
    final = job/'JUDGMENT_SEAL.json'
    if final.exists():
        verify(final, sha(final))
        return final
    started = time.time()
    write(job/'STATUS.json', dict(status='RUNNING', bank='E118', phase='part_b', pid=os.getpid(), start_epoch=started))
    terminals, audits, bindings = [], [], []
    try:
        with channel_type(dest/'INPUT_SEAL.json', sha(dest/'INPUT_SEAL.json'), admission, key) as channel:
            for call in channel.calls:
                schema = call['rendered']['schema']['schema']
                terminal, audit = channel.call(call['id'], lambda v, s=schema: validate_schema(v, s))
                require(terminal['id'] == call['id'], 'exact call/terminal identity')
                raw = channel.root/'ledger'/('E118_'+call['phase'])/(terminal['request_id']+'.response.json')
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
            write(job/'STATUS.json', dict(status='COMPLETE', bank='E118', phase='part_b', pid=os.getpid(), start_epoch=started, completed_epoch=time.time()))
            first = min(Path(b['path']).stat().st_mtime for b in bindings)
            write(final, dict(experiment='E118', phase='belief_wrong_consistency_judging', status='COMPLETE',
                first_output_utc=datetime.fromtimestamp(first, timezone.utc).isoformat(),
                first_output_source='earliest retained physical response file mtime',
                input_seal_sha256=sha(dest/'INPUT_SEAL.json'), source_seal_sha256=sha(transport.HERE/'SOURCE_SEAL.json'),
                E118b_source_seal_sha256=sha(SOURCE), allocation_sha256=sha(dest/'ADMISSION.json'),
                route_verified=True, labels_cpu_only=True, redaction_audit_complete=True, redacted_records=0,
                files={p.name: sha(p) for p in job.iterdir() if p.is_file() and p != final}))
        return final
    except BaseException as exc:
        write(job/'STATUS.json', dict(status='PAUSED_402' if isinstance(exc, runner.funded.CreditPause) else 'STOPPED',
            bank='E118', phase='part_b', error_type=type(exc).__name__, pid=os.getpid(), start_epoch=started))
        raise


def run(dest):
    source_gate()
    transport.unpaused()
    a = read(dest/'ADMISSION.json')
    require(a['input_sha256'] == sha(dest/'INPUT_SEAL.json') and a['E118b_source_seal_sha256'] == sha(SOURCE), 'source/input admission')
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
    require('E118' in current['open_banks'], 'same canonical lifetime1 continuation must be OPEN')
    original = verify(runner.CACHE/'E118/complete/JUDGMENT_SEAL.json',
        '1780b3a7c66c613259614b9c27781393610d958c80b1ccb5f5e01f0ce85e1070')
    require(original['status'] == 'COMPLETE_JUDGING_BANK', 'part a immutable')
    receipt = transport.SHARED/'E118/CONTINUATION_PART_B_C.json'
    require(sha(receipt) == a['continuation_receipt_sha256'], 'posted explicit original-cap continuation')
    r = read(receipt)
    actual, unknown = bank_actual(transport.SHARED/'E118/ledger')
    require(r['bank'] == 'E118' and Decimal(r['lifetime_cap_usd']) == CAP and
            Decimal(r['prior_actual_usd']) == Decimal('.027057') and unknown == 0 and actual >= Decimal(r['prior_actual_usd']),
            'original spend retained/unknown0/no phase allowance reset')
    old = read(dest/'CPU_PREFLIGHT.json')
    require(runner.preflight(dest) == old, 'unchanged whole-source/full-wire privacy inventory')
    write(dest/'DISPATCH_GLOBAL_PROOF.PRIVATE.json', current)
    key = os.environ.get('OPENROUTER_API_KEY')
    require(bool(key), 'credential unavailable')
    with worker():
        return acquire(dest, a, E118bTransport, key)


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
