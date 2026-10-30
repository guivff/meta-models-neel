"""E35 blind latent-label preparation and validation; frozen 2026-10-25.

Pure CPU helpers. Production use requires a passing SAE gate and committed rubric
and prompt; these helpers do not call a judge or inspect experiment files.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter

import numpy as np

SEED = 20261025
DEV_ITEMS = 2100
N_LATENTS = 300
N_CONTEXTS = 20
N_DOUBLE_CODED = 30
LABELS = ('structure', 'content', 'other')
ANNOTATION_FIELDS = frozenset({'blind_id', 'label', 'short_name', 'rationale', 'evidence_indices'})
DISPATCH_FIELDS = frozenset({'schema', 'pins_frozen_before_dispatch', 'secondary_blinded_to_primary',
                             'rubric_sha256', 'prompt_sha256', 'private_key_sha256', 'primary', 'secondary'})
JUDGE_FIELDS = frozenset({'provider', 'model', 'revision', 'session_id', 'decoding',
                         'blind_ids_sha256', 'payloads_sha256'})


def canonical_sha256(value):
    """Canonical JSON identity: sorted keys, UTF-8, compact separators, no newline."""
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _blind_id(value):
    return (isinstance(value, str) and len(value) == 33 and value[0] == 'B'
            and all(c in '0123456789abcdef' for c in value[1:]))


def _digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _rank(domain, value, seed):
    return hashlib.sha256(f'E35|{seed}|{domain}|{value}'.encode()).hexdigest()


def select_top_latents(dev_activation_sums, n_dev_items=DEV_ITEMS):
    """Top 300 mean activations over all 2100 dev items; ties use latent index.

    Sums may be accumulated in streamed batches. Zero activations count in the
    denominator; frequency or mean conditional on firing is not substituted.
    """
    if type(n_dev_items) is not int or n_dev_items != DEV_ITEMS:
        raise ValueError('exactly 2100 dev items required for latent selection')
    totals = np.asarray(dev_activation_sums, dtype=np.float64)
    if totals.ndim != 1 or len(totals) < N_LATENTS or not np.isfinite(totals).all() or (totals < 0).any():
        raise ValueError('finite nonnegative per-latent sums required')
    means = totals / n_dev_items
    return np.lexsort((np.arange(len(means)), -means))[:N_LATENTS].tolist()


def _positive_context(record):
    if not isinstance(record, dict):
        raise TypeError('context record must be an object')
    for name in ('doc_id', 'text'):
        if not isinstance(record.get(name), str) or not record[name]:
            raise ValueError('nonempty document ID and raw context text required')
    if type(record.get('position')) is not int or record['position'] < 0:
        raise ValueError('nonnegative corpus token position required')
    activation = record.get('activation')
    if type(activation) not in (float, int) or not math.isfinite(activation) or activation < 0:
        raise ValueError('finite nonnegative context activation required')
    span = record.get('target_span')
    if (not isinstance(span, (list, tuple)) or len(span) != 2
            or any(type(v) is not int for v in span)
            or not 0 <= span[0] < span[1] <= len(record['text'])):
        raise ValueError('valid nonempty target character span required')
    return activation > 0


def top_contexts(records):
    """Top 20 positive corpus positions, with deterministic document/position ties.

    The supplied records are from section-79 training documents only. Source-group
    exclusion and the frozen token window are enforced by the collection stage.
    Arbitrary metadata is never forwarded in the returned judge contexts.
    """
    positive, seen = [], set()
    for record in records:
        active = _positive_context(record)
        identity = (record['doc_id'], record['position'])
        if identity in seen:
            raise ValueError('duplicate corpus position in latent contexts')
        seen.add(identity)
        if active:
            positive.append(record)
    if len(positive) < N_CONTEXTS:
        raise ValueError('fewer than 20 positive contexts; do not replace the selected latent')
    chosen = sorted(positive, key=lambda r: (-r['activation'], r['doc_id'], r['position']))[:N_CONTEXTS]
    return [{'index': i + 1, 'text': record['text'], 'target_span': list(record['target_span'])}
            for i, record in enumerate(chosen)]


def build_blind_payloads(selected_latents, contexts_by_latent, seed=SEED):
    """Return (primary_payloads, secondary_payloads, private_key).

    Only the first two outputs may be sent to judges. Keep the key in cache.
    Payload order is an opaque-ID order, not dev-activity rank. Secondary sample
    selection precedes all labels; its context payloads exactly match primary.
    """
    selected = list(selected_latents)
    if (len(selected) != N_LATENTS or len(set(selected)) != N_LATENTS
            or any(type(v) is not int or v < 0 for v in selected)):
        raise ValueError('exactly 300 unique nonnegative latent indices required')
    if set(contexts_by_latent) != set(selected):
        raise ValueError('context bank must cover exactly the selected 300 latents')
    if type(seed) is not int or seed != SEED:
        raise ValueError('registered label-preparation seed required')
    rng = random.Random(_rank('blind-id-stream', 'fixed', seed))
    mapping = {f'B{rng.getrandbits(128):032x}': latent for latent in sorted(selected)}
    if len(mapping) != N_LATENTS:
        raise ValueError('opaque blind-ID collision')
    primary = [{'blind_id': blind_id, 'contexts': top_contexts(contexts_by_latent[latent])}
               for blind_id, latent in sorted(mapping.items())]
    secondary_ids = sorted(mapping, key=lambda key: (_rank('second-judge', key, seed), key))[:N_DOUBLE_CODED]
    secondary_set = set(secondary_ids)
    secondary = [payload for payload in primary if payload['blind_id'] in secondary_set]
    key = {'seed': seed, 'blind_to_latent': mapping, 'secondary_blind_ids': sorted(secondary_ids)}
    return primary, secondary, key


def validate_annotations(records, expected_ids):
    """Strict complete judge result set. Never fill, relabel, or adjudicate."""
    expected = list(expected_ids)
    if len(expected) != len(set(expected)) or len(expected) not in (N_LATENTS, N_DOUBLE_CODED):
        raise ValueError('expected exactly 300 primary or 30 independent secondary IDs')
    annotations = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != ANNOTATION_FIELDS:
            raise ValueError('exact frozen annotation fields required')
        blind_id = record['blind_id']
        if not isinstance(blind_id, str) or blind_id not in expected or blind_id in annotations:
            raise ValueError('unknown or duplicate blind ID')
        if record['label'] not in LABELS:
            raise ValueError('label must be structure, content or other')
        for name, limit in (('short_name', 80), ('rationale', 1200)):
            value = record[name]
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError('bounded nonempty annotation text required')
        evidence = record['evidence_indices']
        if (not isinstance(evidence, list) or not evidence or len(evidence) != len(set(evidence))
                or any(type(v) is not int or not 1 <= v <= N_CONTEXTS for v in evidence)):
            raise ValueError('unique evidence indices in 1..20 required')
        annotations[blind_id] = dict(record)
    if set(annotations) != set(expected):
        raise ValueError('incomplete judge annotations')
    return annotations


def validate_key(key):
    if not isinstance(key, dict) or set(key) != {'seed', 'blind_to_latent', 'secondary_blind_ids'}:
        raise ValueError('exact private blind-key schema required')
    mapping = key['blind_to_latent']
    secondary = key['secondary_blind_ids']
    if (key['seed'] != SEED or not isinstance(mapping, dict) or len(mapping) != N_LATENTS
            or len(set(mapping.values())) != N_LATENTS
            or any(not _blind_id(k) for k in mapping)
            or any(type(v) is not int or v < 0 for v in mapping.values())):
        raise ValueError('invalid private blind mapping')
    expected = sorted(sorted(mapping, key=lambda k: (_rank('second-judge', k, SEED), k))[:N_DOUBLE_CODED])
    if not isinstance(secondary, list) or secondary != expected:
        raise ValueError('secondary IDs differ from seeded blind selection')
    return mapping


def validate_payloads(payloads, expected_ids):
    """Require exact public schemas and complete, opaque-ID-sorted 300/30 sets.

    Text is preserved as evidence. This validates structure and dispatch custody,
    not whether a collector actually selected the corpus's top activations.
    """
    expected = list(expected_ids)
    if (len(expected) not in (N_LATENTS, N_DOUBLE_CODED) or len(set(expected)) != len(expected)
            or any(not _blind_id(value) for value in expected)):
        raise ValueError('complete valid primary or secondary blind-ID set required')
    if not isinstance(payloads, list) or len(payloads) != len(expected):
        raise ValueError('exactly 300 primary or 30 secondary payloads required')
    by_id = {}
    order = []
    for payload in payloads:
        if not isinstance(payload, dict) or set(payload) != {'blind_id', 'contexts'}:
            raise ValueError('public payload may contain only blind_id and contexts')
        blind_id = payload['blind_id']
        if not _blind_id(blind_id) or blind_id not in expected or blind_id in by_id:
            raise ValueError('unknown or duplicate payload blind ID')
        contexts = payload['contexts']
        if not isinstance(contexts, list) or len(contexts) != N_CONTEXTS:
            raise ValueError('exactly 20 contexts per blind payload required')
        for index, context in enumerate(contexts, 1):
            if not isinstance(context, dict) or set(context) != {'index', 'text', 'target_span'}:
                raise ValueError('context metadata outside frozen public schema')
            if type(context['index']) is not int or context['index'] != index:
                raise ValueError('context indices must be ordered integers 1 through 20')
            text, span = context['text'], context['target_span']
            if not isinstance(text, str) or not text:
                raise ValueError('nonempty raw context text required')
            if (not isinstance(span, list) or len(span) != 2 or any(type(v) is not int for v in span)
                    or not 0 <= span[0] < span[1] <= len(text)):
                raise ValueError('valid nonempty public target character span required')
        by_id[blind_id] = payload
        order.append(blind_id)
    if order != sorted(expected):
        raise ValueError('public payloads must be in the frozen opaque-ID order')
    return by_id


def _validate_decoding(settings):
    required = {'temperature', 'top_p', 'max_output_tokens', 'seed'}
    if (not isinstance(settings, dict) or not required <= set(settings)
            or not set(settings) <= required | {'other_parameters'}):
        raise ValueError('explicit frozen decoding fields required')
    temperature, top_p = settings['temperature'], settings['top_p']
    if temperature is not None and (type(temperature) not in (int, float)
                                    or not math.isfinite(temperature) or temperature < 0):
        raise ValueError('temperature must be finite nonnegative or explicitly unsupported')
    if top_p is not None and (type(top_p) not in (int, float) or not math.isfinite(top_p) or not 0 < top_p <= 1):
        raise ValueError('top_p must be in (0,1] or explicitly unsupported')
    if type(settings['max_output_tokens']) is not int or settings['max_output_tokens'] <= 0:
        raise ValueError('positive integer output-token cap required')
    if settings['seed'] is not None and type(settings['seed']) is not int:
        raise ValueError('judge seed must be an integer or explicitly unsupported')
    if 'other_parameters' in settings and not isinstance(settings['other_parameters'], dict):
        raise ValueError('other decoding parameters must be an explicit object')
    try:
        canonical_sha256(settings)
    except (TypeError, ValueError):
        raise ValueError('decoding settings must contain only finite JSON data') from None


def validate_label_custody(primary_payloads, secondary_payloads, key, dispatch, *,
                           rubric_sha256, prompt_sha256):
    """Validate blinded label dispatch against its pre-dispatch manifest.

    Both payload files are mandatory, including identical JSON contents for
    the 30 shared IDs. The manifest has schema E35_LABEL_DISPATCH_V1 and exact
    DISPATCH_FIELDS; each judge has exact JUDGE_FIELDS. Role hashes cover the
    sorted ID list and the exact ordered payload list. private_key_sha256 covers
    canonical JSON key contents, while the enclosing file seal binds file bytes.
    The caller verifies the committed rubric/prompt hashes and sealed manifest;
    declarations alone cannot prove historical timing or an external provider run.
    """
    mapping = validate_key(key)
    primary = validate_payloads(primary_payloads, sorted(mapping))
    secondary = validate_payloads(secondary_payloads, key['secondary_blind_ids'])
    if any(payload != primary[blind_id] for blind_id, payload in secondary.items()):
        raise ValueError('secondary contexts must be identical to the primary subset')
    if not isinstance(dispatch, dict) or set(dispatch) != DISPATCH_FIELDS:
        raise ValueError('exact frozen label-dispatch schema required')
    if (dispatch['schema'] != 'E35_LABEL_DISPATCH_V1'
            or dispatch['pins_frozen_before_dispatch'] is not True
            or dispatch['secondary_blinded_to_primary'] is not True):
        raise ValueError('pre-dispatch pins and independently blinded second judge required')
    if (not _digest(rubric_sha256) or not _digest(prompt_sha256)
            or dispatch['rubric_sha256'] != rubric_sha256 or dispatch['prompt_sha256'] != prompt_sha256
            or dispatch['private_key_sha256'] != canonical_sha256(key)):
        raise ValueError('dispatch rubric, prompt or private-key binding mismatch')
    summaries = {}
    for role, payloads, by_id in (('primary', primary_payloads, primary),
                                 ('secondary', secondary_payloads, secondary)):
        settings = dispatch[role]
        if not isinstance(settings, dict) or set(settings) != JUDGE_FIELDS:
            raise ValueError('complete pinned judge configuration required')
        for field in ('provider', 'model', 'revision', 'session_id'):
            value = settings[field]
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError('nonempty exact provider/model/revision/session pins required')
        if settings['revision'].lower() in {'main', 'master', 'latest', 'default', 'head', 'unknown', 'tbd'}:
            raise ValueError('judge revision must identify a fixed version')
        _validate_decoding(settings['decoding'])
        id_digest, payload_digest = canonical_sha256(sorted(by_id)), canonical_sha256(payloads)
        if settings['blind_ids_sha256'] != id_digest or settings['payloads_sha256'] != payload_digest:
            raise ValueError('pre-dispatch blind-ID set or canonical payload hash mismatch')
        summaries[role] = {'n_payloads': len(payloads), 'blind_ids_sha256': id_digest,
                           'payloads_sha256': payload_digest,
                           'decoding_sha256': canonical_sha256(settings['decoding'])}
    if dispatch['primary']['session_id'] == dispatch['secondary']['session_id']:
        raise ValueError('primary and secondary judges require independent sessions')
    return {'schema': 'E35_LABEL_CUSTODY_V1', 'status': 'VERIFIED',
            'primary': summaries['primary'], 'secondary': summaries['secondary'],
            'secondary_payloads_identical_to_primary_subset': True,
            'rubric_sha256': rubric_sha256, 'prompt_sha256': prompt_sha256,
            'private_key_sha256': canonical_sha256(key), 'dispatch_sha256': canonical_sha256(dispatch)}


def structure_mask(primary_records, key, d_sae):
    mapping = validate_key(key)
    if type(d_sae) is not int or d_sae <= max(mapping.values()):
        raise ValueError('dictionary width must contain every selected latent')
    primary = validate_annotations(primary_records, sorted(mapping))
    mask = np.zeros(d_sae, dtype=bool)
    for blind_id, record in primary.items():
        if record['label'] == 'structure':
            mask[mapping[blind_id]] = True
    return mask


def cohen_kappa(primary_records, secondary_records, key):
    """Descriptive unweighted three-category Cohen kappa on the frozen 30 IDs."""
    mapping = validate_key(key)
    primary = validate_annotations(primary_records, sorted(mapping))
    ids = key['secondary_blind_ids']
    secondary = validate_annotations(secondary_records, ids)
    a = Counter(primary[key]['label'] for key in ids)
    b = Counter(secondary[key]['label'] for key in ids)
    observed = sum(primary[key]['label'] == secondary[key]['label'] for key in ids) / N_DOUBLE_CODED
    expected = sum(a[label] * b[label] for label in LABELS) / N_DOUBLE_CODED**2
    kappa = None if expected == 1 else (observed - expected) / (1 - expected)
    confusion = {left: {right: sum(primary[key]['label'] == left and secondary[key]['label'] == right
                                  for key in ids) for right in LABELS} for left in LABELS}
    return {'n_double_coded': N_DOUBLE_CODED, 'labels': list(LABELS), 'observed_agreement': observed,
            'expected_agreement': expected, 'cohen_kappa': kappa,
            'kappa_status': 'UNDEFINED_CONSTANT_MARGINALS' if kappa is None else 'DEFINED',
            'confusion': confusion, 'primary_labels_changed': False}
