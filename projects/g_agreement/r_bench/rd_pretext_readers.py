"""R-D §42 native scoring. Imports are CPU-only until a guarded backend call.

Records flatten the frozen item and an AVAILABLE position window: id, prefilled,
position, split, family, dispreferred, prompt, visible_trace, available. States
are ``(id, prefilled, position, layer) -> vector``. The runner supplies the FULL
frozen donor map and its full one-row-per-item/prefill metadata, even for smoke.
No donor is redrawn for a subset. Returned rows are stamped by the worker.

Workers: NativeBackend(('oracle','jpp_conflict')), NativeBackend(('nla',)),
NativeBackend(()) for text baselines, and AOBackend(isolated_worker=True) in a
fresh process. Call warmup() once, discard its scores, then time the complete
smoke records on that same backend. Model setup is lazy and included in warmup.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import sys
import time
import warnings
from typing import Any, Mapping, Sequence

import numpy as np
from projects.g_agreement.r_bench import rd_pretext as P

PHASE_READERS = {'oracle_jpp': ('oracle', 'jpp_conflict'), 'nla': ('nla',), 'ao': ('ao',), 'base': ()}
BASELINES = ('text_judge', 'prompt_only')
SOURCE_FILES = (
    'projects/g_agreement/r_bench/rd_pretext_readers.py', 'projects/g_agreement/r_bench/rd_pretext.py',
    'projects/g_agreement/r_bench/exact_prefix.py', 'projects/g_agreement/r_bench/x4_cue_run.py',
    'projects/g_agreement/core/config.py', 'projects/g_agreement/core/model.py',
    'projects/g_agreement/core/readers.py', 'projects/g_agreement/core/scoring_lo.py',
    'projects/g_agreement/core/generate.py', 'projects/g_agreement/core/accounting.py',
    'projects/g_agreement/core/edit.py', 'projects/g_agreement/r_bench/bank.py',
    'projects/g_agreement/r_bench/collect.py', 'projects/g_agreement/r_bench/datasets.py',
    'projects/r_panel/setup.py', 'projects/r_panel/pairs.py',
    'projects/r_gemma/config.py', 'projects/r_gemma/gemma.py',
    'projects/r_gemma/oracle.py', 'projects/r_gemma/collect.py',
)


def finite(value: Any) -> float:
    if isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError('nonfinite/invalid R-D score')
    return float(value)


def vector(value: Any) -> np.ndarray:
    if hasattr(value, 'detach'):
        value = value.detach().float().cpu().numpy()
    out = np.asarray(value, dtype=np.float32)
    if out.ndim != 1 or not len(out) or not np.isfinite(out).all() or not np.linalg.norm(out):
        raise ValueError('state must be finite nonzero 1D vector')
    return out


def key(record: Mapping[str, Any]) -> tuple[str, str, str]:
    return record['id'], record['prefilled'], record['position']


def validate_records(records: Sequence[Mapping[str, Any]]) -> None:
    if not records or len({key(r) for r in records}) != len(records):
        raise ValueError('empty or duplicate R-D records')
    roles = {'pool': set(), 'test': set()}
    for r in records:
        P.donor_key(r)
        if r['split'] not in roles or not isinstance(r['family'], str) or not r['family']:
            raise ValueError('invalid role/family: ' + repr(key(r)))
        if type(r['dispreferred']) not in (bool, int) or r['dispreferred'] not in (0, 1):
            raise ValueError('invalid disagreement label: ' + repr(key(r)))
        if 'preferred' in r and bool(r['dispreferred']) != (r['prefilled'] != r['preferred']):
            raise ValueError('changed frozen disagreement label: ' + repr(key(r)))
        P.visible_text(r, r)
        roles[r['split']].add(r['family'])
    if roles['pool'] & roles['test']:
        raise ValueError('pool/test family overlap')


def reader_view(record: Mapping[str, Any]) -> dict[str, str]:
    # Strict allowlist: metadata, labels and other/future continuations cannot leak.
    return {'visible_text': P.visible_text(record, record)}


def _row(record: Mapping[str, Any], arm: str, score: Any, outputs: Mapping[str, Any]) -> dict[str, Any]:
    if arm not in P.ARMS_BY_POSITION[record['position']] or not outputs:
        raise ValueError('unregistered arm or empty outputs: ' + str((key(record), arm)))
    return {name: record[name] for name in ('id', 'prefilled', 'position', 'split', 'family', 'dispreferred')} | {
        'arm': arm, 'score': finite(score), 'outputs': dict(outputs)}


def _check_scored(scored: Sequence[Mapping[str, Any]], count: int, name: str) -> None:
    if len(scored) != count:
        raise ValueError('backend row count mismatch: ' + name)
    for row in scored:
        finite(row['score'])
        if not isinstance(row.get('outputs'), dict) or not row['outputs']:
            raise ValueError('backend empty outputs: ' + name)


def score_readers(records: Sequence[Mapping[str, Any]], states: Mapping[tuple, Any], backend: Any,
                  readers: Sequence[str] = P.READERS, *, donors: Mapping[str, str],
                  donor_records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Fixed full-bank donors, recipient text, same-position/layer donor state."""
    validate_records(records)
    if not readers or len(set(readers)) != len(readers) or any(r not in P.READERS for r in readers):
        raise ValueError('unknown/duplicate reader')
    if dict(donors) != P.donor_plan(donor_records):
        raise ValueError('donor map differs from full frozen construction')
    identities = {P.donor_key(r): r for r in donor_records}
    for r in records:
        identity = identities.get(P.donor_key(r))
        if identity is None or any(identity[k] != r[k] for k in ('split', 'family')):
            raise ValueError('recipient differs from full frozen donor metadata')
    rows, views = [], [reader_view(r) for r in records]
    for reader in readers:
        layer = P.LAYERS[reader]
        for condition in P.STATE_CONDITIONS:
            source = [P.donor_key(r) if condition == 'natural' else donors[P.donor_key(r)] for r in records]
            state_keys = [(*s.rsplit('|', 1), r['position'], layer) for s, r in zip(source, records)]
            H = np.stack([vector(states[k]) for k in state_keys])
            scored = backend.score_batch(reader, views, H)
            _check_scored(scored, len(records), reader + '/' + condition)
            for r, donor, result in zip(records, source, scored):
                rows.append(_row(r, reader + '/' + condition, result['score'], result['outputs'] | {
                    'state_condition': condition, 'state_source_key': donor, 'layer': layer,
                    'state_position': r['position'], 'donor_plan_sha256': P.digest(dict(donors))}))
    return rows


def score_baselines(records: Sequence[Mapping[str, Any]], backend: Any,
                    arms: Sequence[str] = BASELINES) -> list[dict[str, Any]]:
    validate_records(records)
    if len(set(arms)) != len(arms) or any(a not in BASELINES for a in arms):
        raise ValueError('unknown/duplicate text baseline')
    rows = []
    for arm in arms:
        chosen = [r for r in records if arm in P.ARMS_BY_POSITION[r['position']]]
        if not chosen:
            continue  # prompt_only at a is structurally N/A, never a zero-score row.
        messages = [(P.text_judge_messages if arm == 'text_judge' else P.prompt_only_messages)(r, r) for r in chosen]
        scored = backend.score_text_batch(arm, messages)
        _check_scored(scored, len(chosen), arm)
        rows.extend(_row(r, arm, s['score'], s['outputs']) for r, s in zip(chosen, scored))
    return rows


def fit_probes(records: Sequence[Mapping[str, Any]], states: Mapping[tuple, Any], *,
               expected_pool_keys: Sequence[str] | None = None) -> dict[str, Any]:
    """New position-specific fits. Only pool states/labels enter fit or scaling."""
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.exceptions import ConvergenceWarning
    validate_records(records)
    pool = [r for r in records if r['split'] == 'pool']
    expected = {('|'.join(k) if isinstance(k, (tuple, list)) and len(k) == 2 else k) for k in expected_pool_keys} if expected_pool_keys is not None else {P.donor_key(r) for r in pool}
    if not expected or (expected_pool_keys is None and len(expected) != 182):
        raise ValueError('probe requires all 182 frozen pool-prefill keys')
    fits = {'layer': 44, 'pool_keys': sorted(expected), 'pool_families': sorted({r['family'] for r in pool}),
            'positions': {}, 'config': dict(P.PROBE_CONFIG)}
    positions = [p for p in P.POSITIONS if any(r['position'] == p for r in records)]
    for position in positions:
        chosen = sorted((r for r in pool if r['position'] == position), key=P.donor_key)
        if {P.donor_key(r) for r in chosen} != expected:
            raise ValueError('incomplete frozen pool coverage at ' + position)
        H = np.stack([vector(states[(*key(r), 44)]) for r in chosen]).astype(np.float64)
        y = np.array([int(r['dispreferred']) for r in chosen])
        if set(y) != {0, 1}:
            raise ValueError('probe pool requires both disagreement classes')
        scaler = StandardScaler().fit(H)
        with warnings.catch_warnings():
            warnings.simplefilter('error', ConvergenceWarning)
            model = LogisticRegression(C=1., solver='lbfgs', max_iter=2000, random_state=0).fit(scaler.transform(H), y)
        fits['positions'][position] = {'mean': scaler.mean_.tolist(), 'scale': scaler.scale_.tolist(),
            'coef': model.coef_[0].tolist(), 'intercept': float(model.intercept_[0]), 'classes': model.classes_.tolist(),
            'pool_keys': [P.donor_key(r) for r in chosen], 'labels_sha256': P.digest(y.tolist()),
            'states_sha256': hashlib.sha256(np.ascontiguousarray(H, dtype='<f8').tobytes()).hexdigest()}
    fits['fit_sha256'] = P.digest(fits)
    return fits


def score_probes(records: Sequence[Mapping[str, Any]], states: Mapping[tuple, Any], fits: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_records(records)
    if P.digest({k: v for k, v in fits.items() if k != 'fit_sha256'}) != fits.get('fit_sha256'):
        raise ValueError('frozen probe fit hash mismatch')
    rows = []
    for r in records:
        if r['split'] == 'test' and (P.donor_key(r) in fits['pool_keys'] or r['family'] in fits['pool_families']):
            raise ValueError('test item/family overlaps probe pool')
        f = fits['positions'][r['position']]
        h = vector(states[(*key(r), 44)]).astype(np.float64)
        mean, scale, coef = (np.asarray(f[k]) for k in ('mean', 'scale', 'coef'))
        if f['classes'] != [0, 1] or any(v.shape != h.shape or not np.isfinite(v).all() for v in (mean, scale, coef)) or (scale <= 0).any():
            raise ValueError('invalid frozen probe orientation/tensors')
        value = ((h - mean) / scale) @ coef + finite(f['intercept'])
        rows.append(_row(r, 'probe/L44', value, {'layer': 44, 'fit_sha256': fits['fit_sha256'],
            'position': r['position'], 'trained_role': 'pool', 'raw_logit': finite(value), 'comparison': 'descriptive'}))
    return rows


def teacher_forced_lp(model: Any, rows: Sequence[Sequence[int]], heads: Sequence[int], pad: int,
                      *, embed_fn: Any = None) -> list[float]:
    """Variable heads, right padding and explicit positions; both candidates share a call.

    Right padding keeps NLA's native marker at its frozen absolute index. Uses
    the exact-prefix batching convention and only sums candidate token logp.
    """
    import torch
    from projects.g_agreement.r_bench import exact_prefix as E
    if not rows or len(rows) != len(heads) or any(not 0 < h < len(r) for r, h in zip(rows, heads)):
        raise ValueError('invalid teacher-forced row/head boundary')
    dev = next(model.parameters()).device
    ids, mask, positions, _ = E._padded(rows, pad, dev, side='right')
    keep = ids.shape[1] - min(heads) + 1
    kw = {'attention_mask': mask, 'position_ids': positions, 'use_cache': False}
    with torch.no_grad():
        kw['inputs_embeds' if embed_fn is not None else 'input_ids'] = embed_fn(ids) if embed_fn is not None else ids
        try:
            logits = model(logits_to_keep=keep, **kw).logits
        except TypeError as error:
            if 'logits_to_keep' not in str(error):
                raise
            logits = model(**kw).logits
        if logits.shape[1] == ids.shape[1]:
            offset = 0
        elif logits.shape[1] == keep:
            offset = ids.shape[1] - keep
        else:
            raise RuntimeError('unexpected teacher-forced logits shape')
        # Gather selected logits before float32 conversion to avoid a full fp32
        # B x sequence x vocabulary copy when visible prefixes differ in length.
        out = []
        for i, (r, h) in enumerate(zip(rows, heads)):
            pred = torch.arange(h-1, len(r)-1, device=logits.device)-offset
            lp = torch.log_softmax(logits[i, pred].float(), dim=-1)
            target = ids[i, h:len(r)].to(logits.device)
            out.append(float(lp.gather(-1, target[:, None]).sum()))
    return out


class NativeBackend:
    """Lazy base/Oracle/J++ or separate NLA worker, guarded before every forward."""
    def __init__(self, readers: Sequence[str] = (), *, receipt: Mapping[str, Any] | None = None,
                 batch_size: int = 16, target: Any = None):
        if len(set(readers)) != len(readers) or any(r not in ('oracle', 'nla', 'jpp_conflict') for r in readers):
            raise ValueError('invalid native reader group')
        if 'nla' in readers and len(readers) != 1:
            raise ValueError('NLA requires a separate worker')
        if type(batch_size) is not int or batch_size < 2 or batch_size % 2:
            raise ValueError('paired scoring batch must be positive/even, at least 2')
        self.readers, self.receipt, self.batch_size = tuple(readers), receipt, batch_size
        self.target, self.owns_target = target, target is None
        self.oracle = self.nla = None
        self._jpp_cache = {}
        self._source_checked = False

    def __enter__(self): return self
    def __exit__(self, *error): self.close()

    def _check_time(self):
        if self.receipt is None:
            raise RuntimeError('R-D backend requires live guarded deadline receipt')
        receipt = dict(self.receipt)
        if receipt.get('phase') in ('run', 'worker'): receipt['phase'] = 'readers'
        if receipt.get('phase') not in ('readers', 'smoke'):
            raise RuntimeError('reader backend requires readers/smoke phase receipt')
        P.validate_guard_receipt(receipt, own_pod_id=receipt.get('pod_id', ''), now=time.time(),
            expected_source_hashes=receipt.get('source_hashes', {}), phase=receipt['phase'])
        if not self._source_checked:
            root = Path(__file__).resolve().parents[3]
            for name in SOURCE_FILES:
                actual = hashlib.sha256((root/name).read_bytes()).hexdigest()
                if receipt['source_hashes'].get(name) != actual:
                    raise RuntimeError('unfrozen/changed reader dependency: ' + name)
            self._source_checked = True

    def _target(self):
        self._check_time()
        if self.target is None:
            from projects.g_agreement.core import model as M
            self.target = M.load_target()
        return self.target

    def close(self):
        from projects.g_agreement.core import model as M
        if self.nla is not None:
            self.nla.unload(); self.nla = None
        self.oracle = None
        self._jpp_cache.clear()
        if self.target is not None and self.owns_target:
            M.unload(self.target)
        self.target = None

    def score_batch(self, reader: str, views: Sequence[Mapping[str, str]], H: Any) -> list[dict[str, Any]]:
        if reader not in self.readers:
            raise ValueError('reader not enabled: ' + reader)
        self._check_time()
        H = np.asarray(H, dtype=np.float32)
        if H.ndim != 2 or len(H) != len(views) or not len(H) or not np.isfinite(H).all() or (np.linalg.norm(H, axis=1) == 0).any():
            raise ValueError('invalid reader state matrix')
        if any(set(v) != {'visible_text'} or not isinstance(v['visible_text'], str) for v in views):
            raise ValueError('reader context must use strict visible-text allowlist')
        if reader == 'jpp_conflict':
            return self._score_jpp(H)
        return self._score_verbal(reader, views, H)

    def _score_verbal(self, reader, views, H):
        import torch
        from projects.g_agreement.core import config as C, model as M, readers as R, scoring_lo as LO
        from projects.g_agreement.r_bench import exact_prefix as E
        if reader == 'oracle':
            target = self._target()
            if self.oracle is None: self.oracle = R.OLensReader().bind(target)
            model, tok, completions = target.model, target.tokenizer, P.ORACLE_CHOICES
        else:
            if self.nla is None: self.nla = R.NLAReader().bind()
            model, tok, completions = self.nla.model, self.nla.tokenizer, P.NLA_CHOICES
        out = []
        for start in range(0, len(views), self.batch_size//2):
            self._check_time()
            chosen = views[start:start+self.batch_size//2]
            full, heads, slots = [], [], []
            for view in chosen:
                text = view['visible_text']
                if reader == 'oracle':
                    head, slot, _, _ = R.olens_carrier(tok, 44, C.OLENS_PROMPT+'\n'+text.replace('{','{{').replace('}','}}'))
                else:
                    head = M.chat_ids(tok, [{'role': 'user', 'content': self.nla.prompt_text+'\n'+text}])
                    slot = self.nla.marker
                    if [i for i, t in enumerate(head) if t == C.NLA_INJECTION_TOKEN_ID] != [slot]:
                        raise RuntimeError('NLA marker moved')
                    if not R.marker_well_formed(head, C.NLA_INJECTION_TOKEN_ID, C.NLA_LEFT_NEIGHBOR_ID, C.NLA_RIGHT_NEIGHBOR_ID):
                        raise RuntimeError('NLA marker malformed')
                    head += LO.encode(tok, P.NLA_PREFIX)
                for completion in completions:
                    full.append(head+LO.encode(tok, completion)); heads.append(len(head)); slots.append(slot)
            vecs = torch.as_tensor(np.repeat(H[start:start+len(chosen)], 2, axis=0))
            pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
            if reader == 'oracle':
                def embed_fn(ids):
                    e = model.get_input_embeddings()(ids).clone()
                    v = vecs.to(e.device).float()
                    e[torch.arange(len(e), device=e.device), torch.tensor(slots, device=e.device)] = (16000*v/v.norm(dim=1,keepdim=True).clamp_min(1e-9)).to(e.dtype)
                    return e
                with E.adapter_context(model, 'default'):
                    values = teacher_forced_lp(model, full, heads, pad, embed_fn=embed_fn)
                injections = len(chosen)*2
                liveness = self.oracle.liveness
            else:
                before = self.nla.n_hook_calls
                self.nla._vec['v'] = vecs
                try: values = teacher_forced_lp(model, full, heads, pad)
                finally: self.nla._vec['v'] = None
                injections = self.nla.n_hook_calls-before
                if injections < 1: raise RuntimeError('NLA injection hook did not fire')
                liveness = self.nla.liveness
            for j, view in enumerate(chosen):
                positive, negative = map(finite, values[2*j:2*j+2])
                out.append({'score': positive-negative, 'outputs': {'candidate_logprobs': [positive, negative],
                    'completions': list(completions), 'visible_text': view['visible_text'], 'question': P.QUESTION,
                    'format': 'native_bullets' if reader == 'oracle' else 'native_explanation',
                    'marker_index': slots[2*j], 'hook_injections': injections, 'adapter_liveness': liveness,
                    'native_output': completions[0 if positive >= negative else 1]}})
        return out

    def _score_jpp(self, H):
        import torch
        from projects.g_agreement.r_bench import x4_cue_run as X
        target = self._target()
        hashes = [hashlib.sha256(np.ascontiguousarray(h).tobytes()).hexdigest() for h in H]
        missing = list(dict.fromkeys(k for k in hashes if k not in self._jpp_cache))
        if missing:
            by_hash = dict(zip(hashes, H))
            native = X.lens_outputs(target, 'jpp', [torch.from_numpy(by_hash[k]) for k in missing], self.receipt)
            if len(native) != len(missing): raise RuntimeError('J++ row count mismatch')
            for k, result in zip(missing, native):
                if result['filter_sha'] != P.READOUT_EXCLUSION_SHA256 or result['excluded_count'] != P.READOUT_EXCLUSION_COUNT or result['checkpoint_sha'] != P.JPP_PIN['sha256']:
                    raise RuntimeError('J++ checkpoint/filter differs from preregistration')
                self._jpp_cache[k] = result
        return [{'score': P.conflict_score(self._jpp_cache[k]['tokens_decoded']), 'outputs': dict(self._jpp_cache[k]) | {
            'positive_tokens': sorted(P.CONFLICT_POSITIVE), 'negative_tokens': sorted(P.CONFLICT_NEGATIVE),
            'readout_rule': 'top10 whole-token strip/lower signed reciprocal rank', 'question_channel': None}}
                for k in hashes]

    def score_text_batch(self, arm: str, messages: Sequence[Sequence[Mapping[str, str]]]) -> list[dict[str, Any]]:
        if arm not in BASELINES or 'nla' in self.readers:
            raise ValueError('base baseline requires a base/Oracle worker')
        from projects.g_agreement.core import model as M, scoring_lo as LO
        from projects.g_agreement.r_bench import exact_prefix as E
        target = self._target(); model, tok = target.model, target.tokenizer
        completions = P.TEXT_JUDGE_CHOICES if arm == 'text_judge' else P.PROMPT_ONLY_CHOICES
        out = []
        for start in range(0, len(messages), self.batch_size//2):
            self._check_time()
            chosen = messages[start:start+self.batch_size//2]
            full, heads = [], []
            for conversation in chosen:
                head = M.chat_ids(tok, list(conversation))
                for completion in completions:
                    full.append(head+LO.encode(tok, completion)); heads.append(len(head))
            pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
            with E.adapter_context(model, None): values = teacher_forced_lp(model, full, heads, pad)
            for j, conversation in enumerate(chosen):
                positive, negative = map(finite, values[2*j:2*j+2])
                out.append({'score': positive-negative, 'outputs': {'candidate_logprobs': [positive, negative],
                    'completions': list(completions), 'messages': list(conversation), 'adapter_name': None,
                    'native_output': completions[0 if positive >= negative else 1],
                    'context': 'fresh_external_observer' if arm == 'text_judge' else 'original_partial_history'}})
        return out


class AOBackend(NativeBackend):
    """Q27 AO initialization must occur in the runner's fresh worker process."""
    def __init__(self, *, receipt=None, batch_size=16, isolated_worker=False):
        if not isolated_worker or any(name in sys.modules for name in ('projects.r_gemma.oracle','projects.r_gemma.gemma','projects.r_gemma.collect')):
            raise RuntimeError('AO requires a fresh dedicated subprocess before r_gemma imports')
        super().__init__((), receipt=receipt, batch_size=batch_size)
        self.readers = ('ao',); self.reader = None; self.liveness = None

    def _load(self):
        self._check_time()
        if self.reader is None:
            from projects.r_panel import setup
            setup.activate('Q27')
            from projects.r_gemma.oracle import AOReader
            from projects.g_agreement.core import readers as R
            from projects.g_agreement.r_bench import exact_prefix as E
            target = self._target()
            self.reader = AOReader('ao').bind(target)
            from projects.g_agreement.r_bench.rd_pretext_ao_render import carrier
            ids, _ = carrier(self.reader, 32, self.reader.fc_question(P.QUESTION, *P.AO_CHOICES))
            with E.adapter_context(target.model, 'ao'):
                self.liveness = R.assert_adapter_live(target.model, self.reader.adapter_dir, ids, adapter_name='ao')

    def score_batch(self, reader, views, H):
        if reader != 'ao': raise ValueError('AO worker only scores ao')
        self._check_time()
        H = np.asarray(H, dtype=np.float32)
        if H.ndim != 2 or len(H) != len(views) or not len(H) or not np.isfinite(H).all() or (np.linalg.norm(H,axis=1)==0).any():
            raise ValueError('invalid AO state matrix')
        if any(set(v) != {'visible_text'} or not isinstance(v['visible_text'],str) for v in views):
            raise ValueError('AO context must use strict visible-text allowlist')
        self._load()
        import torch
        from projects.r_gemma import gemma as GM
        from projects.g_agreement.r_bench import exact_prefix as E
        tok, model = self.target.tokenizer, self.target.model
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        out = []
        for start in range(0,len(views),self.batch_size//2):
            self._check_time()
            chosen = views[start:start+self.batch_size//2]
            full, heads, vecs, slots = [], [], [], []
            for j, view in enumerate(chosen):
                from projects.g_agreement.r_bench.rd_pretext_ao_render import carrier
                head, slot = carrier(self.reader, 32, self.reader.fc_question(view['visible_text'], *P.AO_CHOICES))
                for completion in P.AO_CHOICES:
                    full.append(head+GM.encode(tok,completion)); heads.append(len(head))
                    vecs.append(torch.from_numpy(H[start+j])); slots.append(slot)
            before = self.reader.n_hook_calls
            try:
                with E.adapter_context(model,'ao'):
                    values = GM.teacher_forced_lp(model,full,heads,pad,next(model.parameters()).device,
                                                  before_forward=self.reader._arm(vecs,slots))
            finally: self.reader._disarm()
            injections = self.reader.n_hook_calls-before
            if injections < 1: raise RuntimeError('AO injection hook did not fire')
            for j,view in enumerate(chosen):
                positive,negative = map(finite,values[2*j:2*j+2])
                out.append({'score':positive-negative,'outputs':{'candidate_logprobs':[positive,negative],
                    'completions':list(P.AO_CHOICES),'visible_text':view['visible_text'],'question':P.QUESTION,
                    'format':'native_candidate','literal_marker_encoding':'lossless_space_question_split','marker_index':slots[2*j],'layer_in_prompt':32,
                    'adapter_liveness':self.liveness,'hook_injections':injections,
                    'native_output':P.AO_CHOICES[0 if positive>=negative else 1]}})
        return out

    def score_text_batch(self, *args, **kwargs):
        raise ValueError('AO worker does not score base baselines')

    def close(self):
        if self.reader is not None:
            self.reader.unload(); self.reader = None
        super().close()


def warmup(backend: Any, records: Sequence[Mapping[str, Any]], states: Mapping[tuple, Any], *,
           readers: Sequence[str] = (), baselines: Sequence[str] = ()) -> dict[str, Any]:
    """Discard one fixed pool case per arm; cold setup is explicitly measured."""
    validate_records(records)
    pool = sorted((r for r in records if r['split']=='pool'), key=key)
    if not pool: raise ValueError('reader warmup must use pool only')
    start = time.monotonic(); discarded = []
    for reader in readers:
        r = pool[0]
        scored = backend.score_batch(reader,[reader_view(r)],np.stack([vector(states[(*key(r),P.LAYERS[reader])])]))
        _check_scored(scored,1,reader); discarded.append({'reader':reader,'key':list(key(r))})
    for arm in baselines:
        allowed = [r for r in pool if arm in P.ARMS_BY_POSITION[r['position']]]
        if not allowed: raise ValueError('warmup missing eligible pool position: '+arm)
        r = allowed[0]
        messages = (P.text_judge_messages if arm=='text_judge' else P.prompt_only_messages)(r,r)
        scored = backend.score_text_batch(arm,[messages]); _check_scored(scored,1,arm)
        discarded.append({'reader':arm,'key':list(key(r))})
    return {'setup_including_warmup_s':time.monotonic()-start,'discarded_warmup':discarded,
            'warmup_rows':len(discarded),'timing_kind':'measured','rows_used_for_analysis':0}
