"""Operational process isolation and C's existing physical-retry rules for E95.

E87's wire, validators, schema retry judge and E10 ledger are supplied by the
existing dispatcher. Processes isolate its mutable protocol/digest globals.
"""
import hashlib
import multiprocessing
import time
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from projects.g_agreement.readerbench.io import read, write, sha
from projects.g_agreement.readerbench.scoring import require
from projects.g_agreement.understand.blind_judge import parallel_funded
from projects.g_agreement.understand.blind_judge.internals_c.backend248 import (
    retry_action, retry_id, cap_guard,
)
from projects.g_agreement.understand.blind_judge.internals_c.resume_e340 import book_bound
from projects.g_agreement.understand.blind_judge.internals_c import transport
from projects.g_agreement.understand.blind_judge.internals_c.booked_bounds248 import ledger_bounds

_SEND = None
_STOP = None
_STATE = None


def cost_summary(client):
    original=client.ledger.summary()
    bounds=ledger_bounds(client.ledger.path,'E95')
    upper=Decimal(bounds['total_booked_upper_bound_usd'])
    return dict(booked_usd=original['committed_usd'],
        known_provider_cost_usd=str(Decimal(original['actual_usd'])-upper),
        booked_429_upper_bound_usd=str(upper),
        unknown_physical_reserve_usd=original['unresolved_reserve_usd'],
        lifetime_cap_usd=original['cap_usd'],legacy_ledger_summary=original,
        upper_bound_provenance=bounds)


@contextmanager
def shared_context(spec):
    expected=Path(__file__).resolve().parents[4]/'wt-internals-b/cache/g_agreement/understand/funded_queue'
    require(Path(spec['shared_pacing_root']).resolve()==expected.resolve(), 'canonical C shared pacing and 402 state')
    old_root=parallel_funded.f.CACHE;old_expiry=transport.EXPIRY
    parallel_funded.f.CACHE=expected
    transport.EXPIRY=1793372400
    try:
        transport.unpaused()
        yield
    finally:
        parallel_funded.f.CACHE=old_root;transport.EXPIRY=old_expiry


def _one(task):
    require(not _STOP.is_set(), 'another E95 worker stopped; no additional request')
    try:
        item, attempt = task
        return _SEND([item], attempt)[0]
    except BaseException:
        _STOP.set()
        raise


def _initialize_fixture(send, stop):
    global _SEND, _STOP
    _SEND, _STOP=send, stop


def _initialize_paid(spec, original, stop):
    global _SEND, _STOP, _STATE
    from .judge_dispatch import worker_channel,send_items
    _STOP=stop
    _STATE=worker_channel(spec,original=original)
    _SEND=lambda batch,attempt:send_items(_STATE,batch,attempt)


def probe_worker(unused):
    """Read-only metadata probe through the exact initialized fresh process."""
    import os
    time.sleep(.25)
    routes=_STATE['privacy'].check_route(os.environ['OPENROUTER_API_KEY'])
    return dict(pid=os.getpid(),route_verified=bool(routes),paid_calls=0)


def parallel_judge(items, send, judge, workers=2, observer=None, *, spec=None, original=False):
    require(type(workers) is int and workers == 2, 'E95 planned two isolated workers')
    context = multiprocessing.get_context('spawn');stop=context.Event()
    initializer=_initialize_paid if spec is not None else _initialize_fixture
    args=(spec,original,stop)if spec is not None else(send,stop)
    with context.Pool(workers,initializer=initializer,initargs=args) as pool:
        def send_batch(batch, attempt):
            pids={w.pid for w in pool._pool}
            result=pool.map_async(_one,[(item,attempt)for item in batch],chunksize=1)
            while True:
                try:rows=result.get(timeout=1);break
                except multiprocessing.TimeoutError:
                    if {w.pid for w in pool._pool}!=pids:
                        stop.set()
                        raise RuntimeError('E95 fresh worker died; preserve unknown reservations, no request replay')
            if observer is not None:observer(rows,attempt)
            return rows
        return judge(items,send_batch)


def claim_slot(ledger, interval):
    """E95 owns only its low-rate state; C's pacing/history is never reset."""
    require(interval >= 5, 'at most twelve E95 physical requests per minute')
    state_path = Path(ledger)/'LOW_RATE.json'
    while True:
        transport.unpaused()
        with parallel_funded.pacing_lock():
            shared_path = parallel_funded.f.CACHE/'THROUGHPUT.json'
            shared = read(shared_path) if shared_path.exists() else parallel_funded.initial_pacing()
            own = read(state_path) if state_path.exists() else dict(next_send_epoch=0, rate_limits=0)
            now = time.time()
            # Yield before joining the shared FIFO whenever a priority bank waits.
            waiting = [x for x in shared.get('waiting', []) if x['bank'] != 'E95']
            delay = max(own['next_send_epoch'], shared['cooldown_until_epoch']) - now
            if not waiting and delay <= 0:
                own['next_send_epoch'] = now + interval*(2**min(own['rate_limits'], 5))
                write(state_path, own)
                break
        time.sleep(min(1, max(.1, delay)))
    parallel_funded.claim_slot('E95')


def patch_api(api, io, bank, *, interval=5):
    """Use C backend248 decisions/IDs and e340's original-reserve booking."""
    require(bank == 'E95', 'only the dedicated E95 bank')
    original = api.Client.one
    require(not getattr(original, '_parallel_patched', False), 'isolated original E10 client')

    def one(client, stage, items, taxonomy=None):
        wire = api.P.payload(stage, items, taxonomy)
        digest = io.digest
        base = digest(io.canonical(wire))
        z = r = 0
        saved = None
        try:
            while True:
                if saved is not None:
                    action, delay = retry_action(saved, api.P, z, r, 2)
                    if action in ('rate', 'rate_exhausted'):
                        book_bound(client.root, result['id'], response_path, api.CAP)
                        with parallel_funded.pacing_lock():
                            p = client.root/'LOW_RATE.json'
                            s = read(p)
                            s['rate_limits'] += 1
                            write(p, s)
                    if action in ('rate_exhausted', 'zero_exhausted'):
                        return dict(result, e95_terminal_reason=(
                            'RATE_LIMIT_EXHAUSTED' if action == 'rate_exhausted'
                            else 'UNCHARGED_BACKEND_RETRIES_EXHAUSTED'))
                    if action == 'decode':
                        return result
                    until = response_path.stat().st_mtime + delay
                    while time.time() < until:
                        require(time.time() < 1793372400, 'paid cutoff during backoff')
                        time.sleep(min(1, until-time.time()))
                    if action == 'rate':
                        r += 1
                    else:
                        z += 1
                    rid = retry_id(base, z, r)
                else:
                    rid = base
                response_path = client.root/stage/(rid+'.response.json')
                require(not response_path.exists()
                        and not response_path.with_name(rid+'.request.json').exists(),
                        'never replay a reserved or previously completed physical request')
                io.digest = lambda value, rid=rid: rid
                claim_slot(client.root, interval)
                transport.unpaused()
                require(_STOP is None or not _STOP.is_set(), 'another E95 worker stopped')
                cap_guard(api, client, original, api.CAP)
                result = original(client, stage, items, taxonomy)
                require(response_path.exists(), 'unsent/unknown response: stop without resend')
                saved = read(response_path)
                if saved['http_status'] == 402:
                    return result  # The existing E95 dispatcher sets the shared latch.
                require(not client.latch.is_set(), 'E95 API failure latch')
                if saved['http_status'] != 429:
                    require(result['id'] in client.ledger.totals()[1], 'explicit charge before continuation')
        finally:
            io.digest = digest

    one._e95_staged_patched = True
    api.Client.one = one
    return original
