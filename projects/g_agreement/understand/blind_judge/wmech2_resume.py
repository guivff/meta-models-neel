"""In-flight reservation settlement and bounded resume for the W-mech2 channel (Guiv 2026-10-28, E79 Arm A).

A request killed mid-flight leaves a reservation with a saved request but no response or result. E10 never
re-reserves an id, so a plain resume stops on it. This entry point:
  settle: books such a reservation at its reserved upper bound through Ledger.settle (never a hand edit),
          writing a hash-bound receipt first; idempotent.
  run:    runs the unchanged wmech2_channel. Only for a settled in-flight id it sends the same wire under a distinct
          deterministic retry id (same stage, own reservation, same allocation); settled successes stay cached.
          An unsettled retry stops, as E10 does; at most MAX_RETRIES per original id.
wmech2_channel.py, its SOURCE_SEAL and START.json are untouched, so the frozen resume binding still holds.
"""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from . import wmech2_channel as channel
from .dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read, write, sha
from projects.g_agreement.readerbench.scoring import require

AUTHORITY = 'Guiv 2026-10-28: in flight at process kill; billing unknown; settle at reserved upper bound; resume with identical ids'
MAX_RETRIES = 1  # W-internals-B review: exactly one replacement retry per in-flight id


def receipt_path(root, stage, rid):
    return Path(root)/stage/(rid+'.inflight_settlement.json')


def retry_id(rid, k):
    return hashlib.sha256(f'INFLIGHT:{rid}:{k}'.encode()).hexdigest()


def settle_inflight(api, root, stage, rid):
    root = Path(root);folder = root/stage
    require(len(rid) == 64 and all(c in '0123456789abcdef' for c in rid), 'request identity')
    request = folder/(rid+'.request.json')
    require(request.exists(), 'saved request required')
    require(not (folder/(rid+'.response.json')).exists() and not (folder/(rid+'.result.json')).exists(), 'not in flight: response or result exists')
    ledger = api.Ledger(root/'ledger.jsonl');book, done = ledger.totals()
    require(rid in book, 'existing reservation required')
    upper = Decimal(read(request)['upper_usd'])
    record = dict(request_id=rid, stage=stage, authority=AUTHORITY, reason='in flight at process kill; billing unknown',
                  actual_usd=str(upper), request_sha256=sha(request))
    path = receipt_path(root, stage, rid)
    if path.exists():require(read(path) == record, 'settlement evidence changed')
    else:
        require(rid not in done, 'prior settlement without this evidence; inspect manually')
        write(path, record)  # Evidence survives interruption before the ledger append.
    if rid not in done:
        require(book[rid] == upper, 'reservation/request bound mismatch')
        ledger.settle(rid, upper)
    else:require(book[rid] == upper, 'prior settlement differs')
    return record


def patch_client(api, io):
    """Wrap Client.one: a settled in-flight id is retried under retry_id(rid, k); everything else is unchanged."""
    original = api.Client.one
    if getattr(original, '_inflight_patched', False):return

    def one(self, stage, items, taxonomy=None):
        wire = api.P.payload(stage, items, taxonomy);rid = io.digest(io.canonical(wire));folder = self.root/stage
        if not receipt_path(self.root, stage, rid).exists() or (folder/(rid+'.response.json')).exists():
            return original(self, stage, items, taxonomy)
        digest = io.digest
        try:
            for k in range(1, MAX_RETRIES+1):
                new = retry_id(rid, k)
                book, _ = self.ledger.totals()
                cut = new in book and not (folder/(new+'.response.json')).exists() and not (folder/(new+'.result.json')).exists()
                if cut and not receipt_path(self.root, stage, new).exists():
                    return {'id': new, 'status': 'MISSING', 'reason': 'PRIOR_RESERVED_NO_RESPONSE_NO_RETRY'}
                if cut:continue
                io.digest = lambda value, new=new: new
                return original(self, stage, items, taxonomy)
            return {'id': retry_id(rid, MAX_RETRIES), 'status': 'MISSING', 'reason': 'INFLIGHT_RETRY_LIMIT'}
        finally:io.digest = digest
    one._inflight_patched = True
    api.Client.one = one


def run(bank, receipt, preflight=False):
    modules = channel.route_modules

    def patched(plan):
        api, privacy, protocol, io = modules(plan);patch_client(api, io);return api, privacy, protocol, io
    channel.route_modules = patched
    try:return channel.run(bank, receipt, preflight)
    finally:channel.route_modules = modules


def main():
    p = argparse.ArgumentParser(description=__doc__);sub = p.add_subparsers(dest='mode', required=True)
    s = sub.add_parser('settle');s.add_argument('--bank', required=True);s.add_argument('--stage', required=True);s.add_argument('--request-id', required=True)
    r = sub.add_parser('run');r.add_argument('--bank', required=True);r.add_argument('--receipt', type=Path);r.add_argument('--preflight-only', action='store_true')
    a = p.parse_args()
    if a.mode == 'settle':
        api = channel.route_modules(read(channel.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'))[0]
        root = channel.LEDGER_BASE/('wmech2_'+a.bank)
        with dispatch_lock(root/'DISPATCH.lock'):print(json.dumps(settle_inflight(api, root, a.stage, a.request_id), sort_keys=True))
    else:
        require(a.preflight_only or a.receipt is not None, 'Integrator receipt required')
        print(json.dumps(run(a.bank, a.receipt, a.preflight_only), sort_keys=True))


if __name__ == '__main__':main()
