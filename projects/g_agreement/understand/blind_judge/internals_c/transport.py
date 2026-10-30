"""Copy of E107's sealed-call transport pattern for the five C-owned banks.

Each bank runs in its own process. All phases use the existing canonical bank
ledger/lock and shared FIFO/402 state. Frozen messages contain no custody metadata.
"""
import hashlib
import json
import os
import re
import shutil
import time
from decimal import Decimal
from pathlib import Path

from ..run import ROOT, payload
from .. import funded_queue as funded
from ..dispatch_lock import dispatch_lock
from ..parallel_funded import patch_api
from ..operational217 import audit_response
from ..privacy79 import strings
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

HERE = ROOT/'results/g_agreement/understand/blind_judge/internals_c'
SHARED = ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue'
ACCOUNT_PAUSE = ROOT.parent/'cache/g_agreement/JUDGING_ACCOUNT_PAUSE_402.json'
CAPS = {k: Decimal(v) for k, v in
        {'E107':'15', 'E108':'8', 'E109':'6', 'E85':'2', 'E106':'15'}.items()}
EXPIRY = 1793336400  # 2026-10-30 05:00 UTC == Fri 06:00 CET


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def frozen_wire(call, protocol):
    require(set(call) == {'id', 'phase', 'rendered'}, 'sealed call allowlist')
    require(re.fullmatch(r'[0-9a-f]{20,64}', call['id']) is not None, 'opaque ID')
    require(call['phase'] in ('generation', 'extraction', 'judging', 'original'), 'registered phase')
    r = call['rendered']
    require(set(r) == {'system', 'user', 'schema'}, 'literal renderer allowlist')
    require(r['system'] is None or type(r['system']) is str, 'literal system')
    require(type(r['user']) is str and bool(r['user']), 'literal nonempty user')
    wire = payload([], '', 'E56', protocol)
    wire['messages'] = ([dict(role='system', content=r['system'])] if r['system'] is not None else []) + [dict(role='user', content=r['user'])]
    if call['phase'] == 'generation':
        require(r['system'] is None and r['schema'] is None, 'outside text-only message')
        wire['max_tokens'] = 256
    if r['schema'] is None:
        wire.pop('response_format')
    else:
        wire['response_format'] = {'type':'json_schema', 'json_schema':r['schema']}
    require(wire['model'] == 'google/gemini-3.1-flash-lite' and
            protocol.PROVIDER == 'google-vertex/global', 'only registered model/provider')
    return wire


def check_privacy(bank, call, wire, original, protocol):
    require(wire == frozen_wire(call, protocol), 'exact frozen wire including settings')
    try:
        for value in strings(wire['messages']):
            original('extract', [dict(id=call['id'], readout=value)], wire)
        return
    except ValueError:
        # Guiv's separate exact-five ruling, never a general benchmark exemption.
        require(bank == 'E107' and call['phase'] == 'generation', 'no privacy exception for this bank/phase')
        proposal = ROOT/'results/g_agreement/i2/E107_EXACT_BENCHMARK_PATH_EXCEPTION_PROPOSAL.json'
        approval = read(ROOT/'results/g_agreement/i2/E107_EXACT_BENCHMARK_PATH_EXCEPTION_APPROVAL.json')
        require(approval['proposal_sha256'] == sha(proposal) and approval.get('issuer') == 'Guiv' and
                approval.get('answer') == 'Approve only these five exact hash pairs', 'exact-five human approval')
        pair = dict(source_user_utf8_sha256=hashlib.sha256(call['rendered']['user'].encode()).hexdigest(),
                    full_frozen_wire_sha256=hashlib.sha256(canonical(wire).encode()).hexdigest())
        require(pair in read(proposal)['exact_entries'], 'both approved exact hashes required')
        text = '\n'.join(strings(wire['messages']))
        forbidden = [r'\b(?:hf_|sk-or-v1-|sk-proj-)[A-Za-z0-9_-]{16,}',
                     r'/(?:Users|home|workspace|private|tmp)/',
                     r'\b(?:projects|results|cache)/[A-Za-z0-9_.-]+/',
                     r'\b(?:\d{1,3}\.){3}\d{1,3}:\d+',
                     r'(?<![A-Za-z])[CDEcde]:\\[A-Za-z0-9_.-]+']
        require(not any(re.search(p, text) for p in forbidden), 'credential/address/machine identity still forbidden')


def unpaused():
    require(time.time() < EXPIRY, 'standing authorization expired')
    require(not (SHARED/'PAUSED_402.json').exists(), 'all banks paused HTTP402')
    if ACCOUNT_PAUSE.exists():
        require(read(ACCOUNT_PAUSE).get('status') == 'FUNDING_CONFIRMED_RESUMED', 'account HTTP402 pause')


def pause(bank, response_path):
    record = dict(status='HTTP402_PAUSED_ALL_BANKS', bank=bank,
                  at_epoch=time.time(), response_sha256=sha(response_path), retry=False)
    SHARED.mkdir(parents=True, exist_ok=True)
    ACCOUNT_PAUSE.parent.mkdir(parents=True, exist_ok=True)
    write(SHARED/'PAUSED_402.json', record)
    write(ACCOUNT_PAUSE, record)
    raise funded.CreditPause('HTTP402_ACCOUNT_CREDITS')


def decode(call, saved, protocol, validator=None):
    cost=saved.get('response',{}).get('usage',{}).get('cost')
    require(cost is not None, 'unknown charge; stop bank and retain reservation')
    audit = audit_response(saved, protocol)
    choice = saved['response']['choices'][0]
    if call['phase'] == 'generation':
        text = choice['message'].get('content')
        require(type(text) is str, 'generation text required')
        result = dict(id=call['id'], phase='generation', status='GENERATED', text=text,
                      finish_reason=choice['finish_reason'], truncated=choice['finish_reason']=='length',
                      refusal=choice['message'].get('refusal'))
    elif audit.get('terminal_unparseable'):
        result = dict(id=call['id'], phase=call['phase'], status='UNPARSEABLE',
                      reason='CHARGED_LENGTH', result=None)
    elif choice['message'].get('refusal'):
        result = dict(id=call['id'], phase=call['phase'], status='REFUSED', result=None)
    else:
        try:
            content = choice['message']['content']
            value = json.loads(content) if call['rendered']['schema'] is not None else content
            if validator is not None:
                validator(value)
            result = dict(id=call['id'], phase=call['phase'], status='KEPT', result=value)
        except (ValueError, TypeError, KeyError, AssertionError):
            result = dict(id=call['id'], phase=call['phase'], status='UNPARSEABLE',
                          reason='FROZEN_SCHEMA_OR_EVIDENCE_FAILED', result=None)
    return result, audit


def source_gate():
    seal = read(HERE/'SOURCE_SEAL.json')
    for name, digest in seal['files'].items():
        require(sha(ROOT/name) == digest, 'C source pin: '+name)


class Transport:
    def __init__(self, seal_path, seal_sha256, admission, key):
        source_gate()
        self.path = Path(seal_path)
        self.input_sha = seal_sha256
        seal = verify(self.path, seal_sha256)
        self.bank = seal['experiment']
        require(self.bank in CAPS and seal['frozen_before_calls'] is True and
                seal['labels_cpu_only'] is True, 'registered blinded sealed bank')
        require(bool(seal['source_seals']), 'original sealed source provenance')
        for s in seal['source_seals']:
            verify(s['seal'], s['sha256'])
        self.calls = read(self.path.parent/'CALLS.json')
        require(self.calls and len({c['id'] for c in self.calls}) == len(self.calls), 'unique complete phase calls')
        require(len({c['phase'] for c in self.calls}) == 1, 'one immutable phase per process')
        self.phase = self.calls[0]['phase']
        a = admission
        exposure = Decimal(str(a['actual_plus_open_caps_usd']))
        require(a['bank'] == self.bank and a['verified'] is True and a['reservation_included'] is True and
                a['operator'] == 'W-internals-C' and Decimal(str(a['allocation_usd'])) == CAPS[self.bank] and
                CAPS[self.bank] <= exposure <= 1000 and exposure.is_finite(), 'posted bank allocation/global1000')
        require(a['input_sha256'] == seal_sha256 and a['source_seal_sha256'] == sha(HERE/'SOURCE_SEAL.json'), 'source/input-bound admission')
        self.admission = a
        self.key = key
        self.root = SHARED/self.bank
        self.allowed = {c['id']:c for c in self.calls}

    def __enter__(self):
        unpaused()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = dispatch_lock(self.root/'DISPATCH.lock')
        self.lock.__enter__()
        try:
            route, (self.api, self.privacy, self.protocol, self.io) = funded.route_api()
            self.api.CAP = CAPS[self.bank]
            self.io.CACHE = self.root/'ledger/route'
            self.io.CACHE.mkdir(parents=True, exist_ok=True)
            require(sha(route['privacy_proof']) == route['privacy_proof_sha256'], 'account privacy proof')
            shutil.copyfile(route['privacy_proof'], self.io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
            self.routes = self.privacy.check_route(self.key)
            self.saved = (self.protocol.payload, self.protocol.validate, self.privacy.check_wire, self.io.digest)
            self.original_check = self.privacy.check_wire
            for c in self.calls:
                check_privacy(self.bank, c, frozen_wire(c, self.protocol), self.original_check, self.protocol)
            self.client = self.api.Client(self.root/'ledger', self.key)
            book, done = self.client.ledger.totals()
            require(set(book) == done, 'unresolved physical charge; reconcile before resume')
            funded.CACHE = SHARED
            patch_api(self.api, self.io, self.bank)
            self.protocol.payload = lambda stage, batch, unused=None: frozen_wire(self.allowed[batch[0]['id']], self.protocol)
            self.protocol.validate = lambda stage, value, batch, unused=None: value
            self.privacy.check_wire = lambda stage, batch, wire, unused=None: check_privacy(self.bank, self.allowed[batch[0]['id']], wire, self.original_check, self.protocol)
            return self
        except BaseException:
            if hasattr(self, 'saved'):
                self.protocol.payload, self.protocol.validate, self.privacy.check_wire, self.io.digest = self.saved
            self.lock.__exit__(None, None, None)
            raise

    def call(self, call_id, validator=None):
        unpaused()
        c = self.allowed[call_id]
        stage = self.bank+'_'+c['phase']
        prefix = 'WIC:'+stage+':'+self.input_sha+':'+call_id+':'
        self.io.digest = lambda value: hashlib.sha256((prefix+value).encode()).hexdigest()
        result = self.client.one(stage, [dict(id=call_id)])
        path = self.root/'ledger'/stage/(result['id']+'.response.json')
        require(path.exists(), 'unsent/unresolved; no guessed output or resend')
        saved = read(path)
        if saved['http_status'] == 402:
            pause(self.bank, path)
        require(not self.client.latch.is_set(), 'transport bank stopped')
        terminal, audit = decode(c, saved, self.protocol, validator)
        require(result['id'] in self.client.ledger.totals()[1], 'known actual charge settled')
        terminal.update(request_id=result['id'], response_sha256=sha(path), input_sha256=self.input_sha)
        write(path.with_suffix('.terminal.json'), terminal)
        return terminal, dict(audit, request_id=result['id'], response_sha256=sha(path))

    def summary(self):
        return self.client.ledger.summary()

    def __exit__(self, *args):
        self.protocol.payload, self.protocol.validate, self.privacy.check_wire, self.io.digest = self.saved
        return self.lock.__exit__(*args)
