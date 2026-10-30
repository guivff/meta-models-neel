"""Scoped §217 clarification 2 transport wrapper; frozen bank code stays pinned.

Install in the sole dispatch process around the existing E79_ARM_B bank/custody runner.
Each retry uses Client.one and its original reserve-before-send ledger unchanged.
"""
import hashlib
import time
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path

from projects.g_agreement.readerbench.io import read, write, sha
from projects.g_agreement.readerbench.scoring import require

AUTHORITY = '3f9842e1af11940fc9fdc4ff6507773c195f74f6'
REASON = 'UNCHARGED_PROVIDER_ERROR_EXHAUSTED'
MAX_RETRIES = 2
EXPIRY = 1793372400  # Fri 30 Oct 2026 15:00 UTC (§236 amendment4)
ROOT = Path(__file__).resolve().parents[4]
HERE = ROOT / 'results/g_agreement/understand/blind_judge/e79b_bank'


def eligible(saved, protocol):
    """Explicitly uncharged, pinned HTTP200 provider errors only; no inference."""
    body = saved.get('response', {})
    if saved.get('http_status') != 200 or not isinstance(body, dict):
        return False
    if body.get('provider') != protocol.PROVIDER_NAME or body.get('model') not in (protocol.MODEL, protocol.MODEL + '-001'):
        return False
    cost = body.get('usage', {}).get('cost')
    if cost is None or isinstance(cost, bool):
        return False
    try:
        cost = Decimal(str(cost))
    except (InvalidOperation, ValueError):
        return False
    if not cost.is_finite() or cost != 0:
        return False
    choices = body.get('choices', [])
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    errors = [body.get('error'), choice.get('error')]
    codes = [e.get('code') for e in errors if isinstance(e, dict)]
    rate_or_server = any(type(c) is int and (c == 429 or 500 <= c <= 599) for c in codes)
    return choice.get('finish_reason') == 'error' or rate_or_server


def source_gate():
    for name, digest in read(HERE / 'SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT / name) == digest, 'clarification2 source pin')


@contextmanager
def installed(bank, *, sleep=time.sleep, clock=time.time, verify_source=True):
    """Scoped hooks for the existing E79_ARM_B runner; never launches a dispatcher."""
    if verify_source:
        source_gate()
    original = {n: getattr(bank, n) for n in ('patch_api', 'audit_response', 'truncated', 'judge', 'adapt')}
    exhausted = set()
    state = {'terminal_reason': None}
    api_restore = []
    root = bank.SHARED / 'E79_ARM_B'
    audit_path = root / 'judgments/TRANSPORT217C2.json'
    events = read(audit_path) if audit_path.exists() else {}

    def patch(api, io, name):
        original_one = api.Client.one
        original['patch_api'](api, io, name)
        paced = api.Client.one

        def one(client, stage, items, taxonomy=None):
            digest = io.digest
            wire = api.P.payload(stage, items, taxonomy)
            base = digest(io.canonical(wire))
            chain = []
            try:
                for attempt in range(MAX_RETRIES + 1):
                    require(clock() < EXPIRY, 'standing authorization expired')
                    require(not (bank.SHARED / 'PAUSED_402.json').exists(), 'shared402pause')
                    rid = base if attempt == 0 else hashlib.sha256(f'TRANSPORT217C2:{base}:{attempt}'.encode()).hexdigest()
                    if attempt and not (client.root / stage / (rid + '.result.json')).exists():
                        sleep(30 * (2 ** (attempt - 1)))
                        require(clock() < EXPIRY, 'standing authorization expired')
                        require(not (bank.SHARED / 'PAUSED_402.json').exists(), 'shared402pause')
                    io.digest = lambda value, rid=rid: rid
                    result = paced(client, stage, items, taxonomy)
                    rp = client.root / stage / (result['id'] + '.response.json')
                    if not rp.exists():
                        return result  # original budget/reservation guard fails closed upstream
                    saved = read(rp)
                    is_error = eligible(saved, api.P)
                    if is_error or chain:
                        require(result['id'] in client.ledger.totals()[1], 'known charge settled through original Ledger')
                        chain.append(dict(request_id=result['id'], response_sha256=sha(rp), transport_attempt=attempt,
                                          eligible_uncharged_provider_error=is_error))
                        events[base] = dict(stage=stage, attempts=chain, authority=AUTHORITY,
                                            partial_content_policy='diagnostic only; never scored', exhausted=is_error and attempt == MAX_RETRIES)
                        write(audit_path, events)
                    if not is_error:
                        return result
                    if attempt == MAX_RETRIES:
                        exhausted.add(sha(rp))
                        return result
                raise AssertionError('unreachable')
            finally:
                io.digest = digest

        one._parallel_patched = True
        api.Client.one = one
        api_restore.append((api, original_one))

    def response(saved, protocol):
        state['terminal_reason'] = None
        if eligible(saved, protocol):
            # Membership is checked via the persisted final response's parsed value,
            # not any generation ID or untrusted response marker.
            require(any(read(root / 'ledger' / e['stage'] / (e['attempts'][-1]['request_id'] + '.response.json')) == saved
                        and e['attempts'][-1]['response_sha256'] in exhausted
                        for e in events.values() if e.get('exhausted')), 'only exhausted bounded errors become missing')
            state['terminal_reason'] = REASON
            return dict(model=saved['response']['model'], provider=saved['response']['provider'], cost_usd='0',
                        finish_reason='error', terminal_unparseable=True, transport_exhausted=True)
        return original['audit_response'](saved, protocol)

    def terminal(items):
        if state['terminal_reason'] == REASON:
            return [dict(id=x['id'], status='UNPARSEABLE', code=None, terminal_reason=REASON) for x in items]
        return original['truncated'](items)

    def judging(items, send):
        # Reuse the original judge's terminal-length control flow for transport
        # exhaustion, restoring the truthful reason before emitting any record.
        reasons = {}
        def wrapped(batch, attempt):
            rows = send(batch, attempt)
            for row in rows:
                if row.get('terminal_reason') == REASON:
                    reasons[row['id']] = REASON
                    row = row.copy()
                    row['terminal_reason'] = 'CHARGED_LENGTH'
                yield row
        result = original['judge'](items, lambda b, a: list(wrapped(b, a)))
        for row in result:
            if row['id'] in reasons:
                row['terminal_reason'] = REASON
        return result

    def adapting(rows, items):
        view = deepcopy(rows)
        for row in view:
            if row.get('terminal_reason') == REASON:
                row['terminal_reason'] = 'CHARGED_LENGTH'
        flat, audit = original['adapt'](view, items)
        for actual, record in zip(rows, audit):
            if actual.get('terminal_reason') == REASON:
                record['terminal_reason'] = REASON
        return flat, audit

    bank.patch_api, bank.audit_response, bank.truncated, bank.judge, bank.adapt = patch, response, terminal, judging, adapting
    try:
        yield
        path = root / 'judgments/JUDGMENT_SEAL.json'
        if path.exists():
            if not audit_path.exists():
                write(audit_path, events)
            seal = read(path)
            seal['files'][audit_path.name] = sha(audit_path)
            seal.update(transport217c2_finalized=True, transport217c2_authority=AUTHORITY,
                        transport217c2_source_seal_sha256=sha(HERE / 'SOURCE_SEAL.json'))
            write(path, seal)
    finally:
        for api, saved in reversed(api_restore):
            api.Client.one = saved
        for name, value in original.items():
            setattr(bank, name, value)
