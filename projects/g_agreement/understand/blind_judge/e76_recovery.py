"""User-authorized HTTP429 zero settlement and bounded E76 transport recovery.

No credential lookup. The Integrator invokes settlement/dispatch with its key in custody.
"""
import argparse
import hashlib
import time
from decimal import Decimal
from pathlib import Path
from .run import route_modules
from .dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read, sha, write
from projects.g_agreement.readerbench.scoring import require

AUTHORITY = 'Guiv 2026-10-28: rejected, uncharged (HTTP 429); settle through ledger; capped exponential retries, each separately reserved'
MAX_RETRIES = 4
BACKOFF_SECONDS = (5, 10, 20, 40)


def rejected_uncharged(response):
    body = response.get('response', {})
    require(response.get('http_status') == 429 and isinstance(body, dict), 'HTTP429 evidence required')
    require(not body.get('id') and not body.get('choices'), 'generation present; usage reconciliation required')
    require(body.get('usage', {}).get('cost') in (None, 0, '0'), 'charged response cannot be settled at zero')
    require(body.get('error', {}).get('code') == 429, 'provider rejection code required')


def settle_rejection(api, ledger_root, stage, rid):
    """Idempotent, evidence-bound zero settlement; never rewrites ledger/history."""
    root = Path(ledger_root)
    require(stage.startswith('E76_attempt') and len(rid) == 64 and all(c in '0123456789abcdef' for c in rid), 'E76 request identity')
    request = root / stage / (rid + '.request.json')
    response = root / stage / (rid + '.response.json')
    req = read(request); rejected_uncharged(read(response))
    ledger = api.Ledger(root / 'ledger.jsonl')
    book, done = ledger.totals()
    require(rid in book, 'existing reservation required')
    receipt = root / stage / (rid + '.reconciliation.json')
    record = dict(request_id=rid, authority=AUTHORITY, reason='rejected, uncharged (HTTP 429)',
                  actual_usd='0', request_sha256=sha(request), response_sha256=sha(response))
    if receipt.exists():
        require(read(receipt) == record, 'reconciliation evidence changed')
    else:
        require(rid not in done, 'prior settlement without this evidence; inspect manually')
        write(receipt, record)  # Evidence survives interruption before ledger append.
    if rid not in done:
        require(book[rid] == Decimal(req['upper_usd']), 'reservation/request bound mismatch')
        ledger.settle(rid, Decimal('0'))
    else:
        require(book[rid] == 0, 'prior settlement differs')
    return record


def retry_identity(base_id, retry):
    return base_id if retry == 0 else hashlib.sha256(f'E76:HTTP429:{base_id}:{retry}'.encode()).hexdigest()


def one_with_backoff(client, api, io, stage, batch, wire, send_guard, sleep=time.sleep):
    """Only proven uncharged 429s retry. Existing successes and reservations stay intact."""
    original_digest = io.digest
    base_id = original_digest(io.canonical(wire))
    try:
        for retry in range(MAX_RETRIES + 1):
            rid = retry_identity(base_id, retry)
            attempt_stage = stage if retry == 0 else stage + '_429retry' + str(retry)
            io.digest = lambda value, rid=rid: rid
            with send_guard(api, wire):
                result = client.one(attempt_stage, batch)
                if result.get('status') == 'OK':
                    return result, attempt_stage
                response = client.root / attempt_stage / (rid + '.response.json')
                if not response.exists() or read(response).get('http_status') != 429:
                    return result, attempt_stage
                settle_rejection(api, client.root, attempt_stage, rid)
            if retry == MAX_RETRIES:
                raise RuntimeError('E76 HTTP429 retry limit reached; no further send')
            sleep(BACKOFF_SECONDS[retry])
    finally:
        io.digest = original_digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--route', type=Path, required=True)
    p.add_argument('--ledger-root', type=Path, required=True)
    p.add_argument('--request-id', required=True)
    p.add_argument('--stage', default='E76_attempt0')
    p.add_argument('--cap-usd', type=Decimal, default=Decimal('18'))
    a = p.parse_args(); api, _, _, _ = route_modules(read(a.route)); api.CAP = a.cap_usd
    with dispatch_lock(a.ledger_root / 'DISPATCH.lock'):
        result = settle_rejection(api, a.ledger_root, a.stage, a.request_id)
    print(result['reason'] + '; settled USD 0 through Ledger.settle')


if __name__ == '__main__':
    main()
