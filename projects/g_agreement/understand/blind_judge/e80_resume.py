"""Bounded resume for the E80/E80c channel after an uncharged provider error (Guiv 2026-10-28, E80c f4f90fa0).

A provider error inside HTTP 200 (finish_reason 'error', zero tokens, usage cost 0) is settled at USD 0 by E10 and cached
as MISSING, so a plain rerun stops on it again, and the channel refuses an existing output directory. This entry point:
  - keeps an incomplete (non-terminal) bank directory intact under a timestamped name, so the unchanged channel can
    write a fresh one; a terminal directory (JUDGMENTS.json or RESULT_SEAL.json present) is never touched;
  - retries ONLY a proven uncharged provider error, once, under a distinct deterministic id in the same stage with its
    own reservation; every cached success or other failure is returned unchanged; an unresolved reservation is never resent.
e80_channel.py and its ROUTE_SEAL are untouched.
"""
import argparse
import hashlib
import time
from pathlib import Path
from . import e80_channel as channel
from projects.g_agreement.readerbench.io import read
from projects.g_agreement.readerbench.scoring import require

MAX_RETRIES = 1


def retry_id(rid, k):
    return hashlib.sha256(f'E80:UNCHARGED_PROVIDER_ERROR:{rid}:{k}'.encode()).hexdigest()


def uncharged_provider_error(saved):
    """HTTP 200 whose only choice ends in finish_reason 'error' with zero tokens and zero cost."""
    body = saved.get('response') or {}
    if saved.get('http_status') != 200 or not isinstance(body, dict) or not body.get('choices'):return False
    usage = body.get('usage') or {}
    return (body['choices'][0].get('finish_reason') == 'error' and usage.get('cost') in (0, 0.0, '0')
            and not usage.get('prompt_tokens') and not usage.get('completion_tokens'))


def patch_client(api, io):
    original = api.Client.one
    if getattr(original, '_uncharged_patched', False):return

    def one(self, stage, items, taxonomy=None):
        wire = api.P.payload(stage, items, taxonomy);rid = io.digest(io.canonical(wire));folder = self.root/stage
        response = folder/(rid+'.response.json')
        if not response.exists() or not uncharged_provider_error(read(response)):
            return original(self, stage, items, taxonomy)
        book, done = self.ledger.totals()
        require(rid in done and book[rid] == 0, 'original uncharged error must be settled at USD 0')
        digest = io.digest
        try:
            for k in range(1, MAX_RETRIES+1):
                new = retry_id(rid, k)
                if new in book and new not in done:
                    return {'id': new, 'status': 'MISSING', 'reason': 'PRIOR_RESERVED_NO_RESPONSE_NO_RETRY'}
                io.digest = lambda value, new=new: new
                return original(self, stage, items, taxonomy)
        finally:io.digest = digest
    one._uncharged_patched = True
    api.Client.one = one


def set_aside(bank_dir):
    bank_dir = Path(bank_dir)
    if not bank_dir.exists():return None
    require(not (bank_dir/'JUDGMENTS.json').exists() and not (bank_dir/'RESULT_SEAL.json').exists(), 'terminal bank directory: no resume')
    kept = bank_dir.with_name(bank_dir.name+'_INCOMPLETE_'+time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    bank_dir.rename(kept);return kept


def charged_length_truncation(saved):
    """HTTP 200, the pinned provider's choice ended by max_tokens (finish_reason 'length'), with a charged usage cost."""
    body = saved.get('response') or {}
    if saved.get('http_status') != 200 or not isinstance(body, dict) or not body.get('choices'):return False
    return body['choices'][0].get('finish_reason') == 'length' and (body.get('usage') or {}).get('cost') is not None


class TerminalOnTruncation:
    """§212 (Guiv): a charged length truncation is terminal UNPARSEABLE (missing) with no retry. The channel reads a
    non-OK response once per attempt; seen() marks it and presents it as a completed, unparseable reply so the
    channel records UNPARSEABLE, and the attempt loop for that record then ends (no further calls)."""

    def __init__(self):self.terminal = False;self.truncations = []

    def read(self, path):
        value = read(path)
        if str(path).endswith('.response.json') and charged_length_truncation(value):
            self.terminal = True;self.truncations.append(Path(path).name[:64])
            value = json_copy(value);value['response']['choices'][0]['finish_reason'] = 'stop'
        return value

    def range(self, *args):
        self.terminal = False
        for attempt in range(*args):
            yield attempt
            if self.terminal:return


def json_copy(value):
    import json
    return json.loads(json.dumps(value))


def run(spec_path, preflight=False):
    spec = read(spec_path);seal = read(channel.HERE/'ROUTE_SEAL.json')
    modules = channel.route_modules;shim = TerminalOnTruncation()

    def patched(plan):
        api, privacy, protocol, io = modules(plan);patch_client(api, io);return api, privacy, protocol, io
    channel.route_modules = patched;channel.read = shim.read;channel.range = shim.range
    try:
        if not preflight:
            kept = set_aside(Path(seal['ledger_root'])/spec['bank'])
            if kept:print('kept incomplete directory:', kept)
        result = channel.run(spec, preflight)
        print('charged length truncations recorded UNPARSEABLE (no retry):', len(shim.truncations), shim.truncations)
        return result
    finally:
        channel.route_modules = modules;channel.read = read
        if 'range' in vars(channel):del channel.range


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--spec', type=Path, required=True);p.add_argument('--preflight-only', action='store_true')
    a = p.parse_args();run(a.spec, a.preflight_only)


if __name__ == '__main__':main()
