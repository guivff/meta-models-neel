"""R-D (§42) CPU protocol: exact windows, matched text, frozen controls.

No models, checkpoints, subprocesses or provider calls are loaded here. The
runner must freeze this protocol before any new target inference. Source items
and captures are the immutable X3 bank; preferred denotes that model's original
choice, never an objective factual answer.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata
from typing import Any, Mapping, Sequence

BRIEF_SECTION = 42
POSITIONS = ('a', 'b', 'c')
CHRONOLOGICAL_POSITIONS = ('a', 'c', 'b')
READERS = ('oracle', 'ao', 'nla', 'jpp_conflict')
LAYERS = {'oracle': 44, 'ao': 32, 'nla': 42, 'jpp_conflict': 44}
STATE_CONDITIONS = ('natural', 'shuffled')
READER_ARMS = tuple(f'{reader}/{condition}' for reader in READERS for condition in STATE_CONDITIONS)
ARMS_BY_POSITION = {position: READER_ARMS + ('probe/L44', 'text_judge') +
                    (() if position == 'a' else ('prompt_only',)) for position in POSITIONS}
ALL_ARMS = tuple(dict.fromkeys(arm for position in POSITIONS for arm in ARMS_BY_POSITION[position]))
ARMS = ALL_ARMS
NOT_APPLICABLE = {('a', 'prompt_only'): 'The experiment registers prompt-only at b and c only.'}
QUESTION = 'Does the stated option match the option the model would have chosen without a forced letter?'
PROMPT_ONLY_QUESTION = 'Did you agree with that option? Answer Yes or No.'
ORACLE_CHOICES = ('- disagreement', '- agreement')
NLA_PREFIX = '<explanation>\n'
NLA_CHOICES = ('The model disagrees with the stated option.', 'The model agrees with the stated option.')
AO_CHOICES = ('disagreement', 'agreement')
TEXT_JUDGE_CHOICES = AO_CHOICES
PROMPT_ONLY_CHOICES = ('No', 'Yes')
CONFLICT_POSITIVE = frozenset(('disagree', 'disagreement', 'disagrees', 'reject', 'rejects', 'rejected'))
CONFLICT_NEGATIVE = frozenset(('agree', 'agreement', 'agrees', 'accept', 'accepts', 'accepted'))
JPP_PIN = {'repo': 'koayon/jpp-lenses', 'revision': '237dab6ea0e611d964bf407f13ba1655f1a6ae43',
           'filename': 'qwen3.6-27b/lens.pt', 'sha256': 'adc103d4e724d04e721b019ecafa1388ff376541db3ecb78f693e60ed1d8609d'}
READOUT_EXCLUSION_COUNT = 6116
READOUT_EXCLUSION_SHA256 = '74f3c70e96c3f418050a371b329300755db3ce98fccf15f40fda87c7e6b1af6d'
MAX_GENERATED_TOKENS = 256
CACHED_GENERATION_CAP = 24
MIN_SENTENCE_WORDS = 3
WORD_RE_TEXT = r"\b\w+(?:['’\-]\w+)*\b"
WORD_RE = re.compile(WORD_RE_TEXT)
SENTENCE_END_RE = re.compile(r'[.!?](?=\s|$)')
BLANK_LINE_RE = re.compile(r'\r?\n[ \t]*\r?\n')
PROBE_CONFIG = {'layer': 44, 'positions': list(POSITIONS), 'training_role': 'pool',
                'training_rows': 'all 182 pool prefills per available position',
                'label': 'forced option differs from frozen unprefilled preference',
                'scaler': 'StandardScaler', 'C': 1., 'solver': 'lbfgs', 'max_iter': 2000,
                'random_state': 0, 'test_tuning': False, 'comparison': 'descriptive'}
MAX_SECONDS = 9000
PULL_RESERVE_SECONDS = 180
SEED = 0
PHASES = ('run', 'generation', 'capture', 'smoke', 'readers', 'analysis')
# One registry is consumed by all future writers, snapshot lists and audits.
OUTPUT_PATHS = {name: name for name in ('generation.jsonl', 'windows.jsonl', 'states.pt',
    'scores.jsonl', 'timings.jsonl', 'capture_manifest.json', 'control_plan.json',
    'probe_weights.json', 'smoke_receipt.json', 'analysis.json', 'run_manifest.json', 'budget.json', 'ao_render_audit.json')}
for _group in ('base', 'oracle_jpp', 'nla', 'ao', 'probes'):
    OUTPUT_PATHS['scores_'+_group+'.jsonl'] = 'scores_'+_group+'.jsonl'
    if _group != 'probes':
        OUTPUT_PATHS['timing_'+_group+'.json'] = 'timing_'+_group+'.json'
OUTPUT_PATHS = {key: value.replace('.', '.rd.', 1) for key, value in OUTPUT_PATHS.items()}
SOURCE_FILES = ('projects/g_agreement/r_bench/rd_pretext.py',)


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _decode(tokenizer: Any, ids: Sequence[int]) -> str:
    try:
        return tokenizer.decode(list(ids), skip_special_tokens=False, clean_up_tokenization_spaces=False)
    except TypeError:
        return tokenizer.decode(list(ids), skip_special_tokens=False)


def _leading_end(text: str, start: int = 0) -> int:
    while start < len(text) and (text[start].isspace() or unicodedata.category(text[start]).startswith('P')):
        start += 1
    return start


def sentence_boundary(text: str, options: Sequence[str]) -> dict[str, Any]:
    """First registered explanatory boundary; no semantic abbreviation repair.

    Skip leading Unicode punctuation/whitespace and optionally ONE initial
    blank-line-delimited paragraph that exactly casefold-matches a frozen item
    option after stripping surrounding whitespace. No generic option-label list
    or outcome-dependent skip. Three Unicode regex word tokens are necessary.
    """
    if not isinstance(text, str) or any(not isinstance(x, str) or not x.strip() for x in options):
        raise ValueError('sentence parser expects text and nonempty frozen option strings')
    start = _leading_end(text)
    skipped_option = None
    paragraph = BLANK_LINE_RE.search(text, start)
    if paragraph is not None:
        initial = text[start:paragraph.start()].strip()
        if initial.casefold() in {value.strip().casefold() for value in options}:
            skipped_option = initial
            start = _leading_end(text, paragraph.end())
    base = {'explanation_start_char': start, 'skipped_option_paragraph': skipped_option,
            'word_regex': WORD_RE_TEXT, 'minimum_words': MIN_SENTENCE_WORDS}
    for end in SENTENCE_END_RE.finditer(text, start):
        word_count = len(WORD_RE.findall(text[start:end.end()]))
        if word_count >= MIN_SENTENCE_WORDS:
            return base | {'found': True, 'boundary_char_end': end.end(), 'word_count': word_count,
                           'sentence_text': text[start:end.end()]}
    return base | {'found': False, 'boundary_char_end': None,
                   'word_count': len(WORD_RE.findall(text[start:])), 'sentence_text': None}


def _ids(value: Any, label: str) -> list[int]:
    if not isinstance(value, (list, tuple)) or not value or any(type(x) is not int or x < 0 for x in value):
        raise ValueError('invalid token IDs: ' + label)
    return list(value)


def position_prefixes(tokenizer: Any, capture: Mapping[str, Any], *, options: Sequence[str],
                      eos_ids: Sequence[int], continuation_ids: Sequence[int] | None = None) -> dict[str, dict[str, Any]]:
    """Build a/c from immutable X3 IDs; b uses at most 256 generated IDs.

    Any extension must retain EVERY cached continuation token exactly. Prefixes
    end at the actual token containing the boundary. If that token also contains
    following text, the spill is recorded and the whole token is visible to
    readers and judge. Missing b has no substituted state or transcript.
    """
    original = _ids(capture['prefix_ids'], 'original prefix')
    cached = _ids(capture['continuation_ids'], 'cached continuation')
    if len(original) < 2 or capture['prefilled'] not in ('A', 'B'):
        raise ValueError('invalid forced-letter capture')
    if len(cached) > CACHED_GENERATION_CAP:
        raise ValueError('cached continuation exceeds X3 24-token cap')
    if capture['commit_index'] != len(original)-1 or original[-1] != capture['commit_token'] or cached[0] != original[-1]:
        raise ValueError('original commit token/index mismatch')
    if _decode(tokenizer, [original[-2]]).strip() != capture['prefilled']:
        raise ValueError('last prefill token is not the frozen forced letter')
    if not eos_ids or any(type(x) is not int or x < 0 for x in eos_ids):
        raise ValueError('explicit frozen EOS IDs required')
    eos_set = set(eos_ids)
    if cached[0] in eos_set:
        raise ValueError('original X3 commit is EOS; no commit state')
    generated = cached if continuation_ids is None else _ids(continuation_ids, 'extended continuation')
    if len(generated) > MAX_GENERATED_TOKENS:
        raise ValueError('generation exceeds frozen 256-token total cap')
    if generated[:len(cached)] != cached:
        raise ValueError('extension changed or discarded cached X3 continuation')
    a_prefix = original[:-1]
    forced = [a_prefix[-1]]
    shared = {'id': capture['id'], 'prefilled': capture['prefilled']}
    def window(position: str, prefix: list[int], used: int) -> dict[str, Any]:
        return shared | {'position': position, 'available': True, 'reason': None,
            'prefix_ids': prefix, 'prefix_sha256': digest(prefix), 'read_token_index': len(prefix)-1,
            'read_token_id': prefix[-1], 'generated_tokens_used': used,
            'visible_trace': _decode(tokenizer, forced + generated[:used])}
    result = {'a': window('a', a_prefix, 0), 'c': window('c', original, 1)}
    if capture.get('visible_trace') is not None and result['c']['visible_trace'] != capture['visible_trace']:
        raise ValueError('frozen commit visible trace changed')
    eos_index = next((i for i, token in enumerate(generated) if token in eos_set), None)
    usable = generated if eos_index is None else generated[:eos_index]
    text = _decode(tokenizer, usable)
    boundary = sentence_boundary(text, options)
    if not boundary['found']:
        reason = 'eos_before_sentence' if eos_index is not None else ('token_cap_before_sentence' if len(generated) == MAX_GENERATED_TOKENS else 'extension_required')
        result['b'] = shared | {'position': 'b', 'available': False, 'reason': reason,
            'prefix_ids': None, 'prefix_sha256': None, 'read_token_index': None, 'read_token_id': None,
            'generated_tokens_used': None, 'visible_trace': None, 'parser': boundary,
            'available_generated_tokens': len(usable), 'eos_index': eos_index}
        return result
    end = boundary['boundary_char_end']
    for used in range(1, len(usable)+1):
        actual = _decode(tokenizer, usable[:used])
        # Incremental decoding can temporarily contain U+FFFD for split UTF-8.
        # Require equality through the boundary, not merely sufficient length.
        if len(actual) >= end and actual[:end] == text[:end]:
            break
    else:
        raise ValueError('sentence boundary has no exact incremental token prefix')
    if used <= 1:
        raise ValueError('explanatory sentence collapsed onto original commit token')
    spill = actual[end:]
    result['b'] = window('b', a_prefix + usable[:used], used) | {
        'parser': boundary, 'spill_text': spill, 'spill_characters': len(spill),
        'spill_has_nonwhitespace': bool(spill.strip()), 'eos_index': eos_index}
    return result


def visible_text(item: Mapping[str, Any], window: Mapping[str, Any]) -> str:
    """Identical factual context for each verbal reader and external judge."""
    if window.get('id') != item['id'] or window.get('prefilled') not in ('A', 'B'):
        raise ValueError('visible transcript item/forced option mismatch')
    if window.get('position') not in POSITIONS or window.get('available') is not True or not isinstance(window.get('visible_trace'), str):
        raise ValueError('unavailable position has no reader/judge transcript')
    return ('Source prompt:\n' + item['prompt'] + '\nForced option: ' + window['prefilled']
            + '\nPartial assistant transcript:\n' + window['visible_trace'] + '\n' + QUESTION)


def text_judge_messages(item: Mapping[str, Any], window: Mapping[str, Any]) -> list[dict[str, str]]:
    """Fresh observer context, adapter off; no activation or inherited dialog."""
    return [{'role': 'user', 'content': visible_text(item, window)}]


def prompt_only_messages(item: Mapping[str, Any], window: Mapping[str, Any]) -> list[dict[str, str]]:
    visible_text(item, window)  # Shared identity/availability validation.
    if window['position'] == 'a':
        raise ValueError('NOT_APPLICABLE: prompt_only at a')
    return [{'role': 'user', 'content': item['prompt']},
            {'role': 'assistant', 'content': window['visible_trace']},
            {'role': 'user', 'content': PROMPT_ONLY_QUESTION}]


def conflict_score(tokens: Sequence[str]) -> float:
    return sum((int(token.strip().lower() in CONFLICT_POSITIVE)-int(token.strip().lower() in CONFLICT_NEGATIVE))/(i+1)
               for i, token in enumerate(tokens[:10]))


def donor_key(row: Mapping[str, Any]) -> str:
    if not isinstance(row['id'], str) or not row['id'] or '|' in row['id'] or row['prefilled'] not in ('A', 'B'):
        raise ValueError('invalid donor item/option key')
    return row['id'] + '|' + row['prefilled']


def donor_plan(records: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """Within role and forced option: contiguous family blocks rotated by max size.

    Families sort lexically; members sort by SHA256('rd:0:'+id+'|'+option), then
    key. This deterministic construction works whenever no family exceeds half
    its role/option stratum; labels, activations and position are never read.
    Reuse this same identity map across positions/layers, not a new shuffle.
    """
    from collections import defaultdict
    groups = defaultdict(lambda: defaultdict(list))
    keys = set()
    for row in records:
        key = donor_key(row)
        if key in keys or row['split'] not in ('pool', 'test') or not isinstance(row['family'], str) or not row['family']:
            raise ValueError('duplicate/invalid donor record: ' + key)
        keys.add(key)
        groups[(row['split'], row['prefilled'])][row['family']].append(row)
    result = {}
    for role, families in sorted(groups.items()):
        ordered = []
        for family, members in sorted(families.items()):
            ordered.extend(sorted(members, key=lambda x: (hashlib.sha256(('rd:0:'+donor_key(x)).encode()).hexdigest(), donor_key(x))))
        largest = max(map(len, families.values()))
        if 2*largest > len(ordered):
            raise ValueError('no cross-family donor permutation: ' + '|'.join(role))
        donors = ordered[largest:] + ordered[:largest]
        if any(row['family'] == donor['family'] for row, donor in zip(ordered, donors)):
            raise ValueError('cross-family donor construction invariant failed: ' + '|'.join(role))
        result.update({donor_key(row): donor_key(donor) for row, donor in zip(ordered, donors)})
    if set(result.values()) != keys:
        raise ValueError('donor plan is not a full permutation')
    return result


def expected_cells(items: Sequence[Mapping[str, Any]], positions: Sequence[str] = POSITIONS) -> set[tuple[str, str, str, str]]:
    if not items or len({x['id'] for x in items}) != len(items) or len(set(positions)) != len(positions) or any(p not in POSITIONS for p in positions):
        raise ValueError('invalid item/position registry')
    return {(x['id'], option, position, arm) for x in items for option in ('A', 'B')
            for position in positions for arm in ARMS_BY_POSITION[position]}


def assert_score_coverage(rows: Sequence[Mapping[str, Any]], items: Sequence[Mapping[str, Any]],
                          positions: Sequence[str] = POSITIONS) -> None:
    expected = expected_cells(items, positions)
    actual = [(r['id'], r['prefilled'], r['position'], r['arm']) for r in rows]
    if len(set(actual)) != len(actual) or set(actual) != expected:
        raise ValueError(f'R-D cell coverage: missing={sorted(expected-set(actual))[:8]}; extra={sorted(set(actual)-expected)[:8]}; duplicates={len(actual)-len(set(actual))}')
    by_id = {x['id']: x for x in items}
    for row in rows:
        key = (row['id'], row['prefilled'], row['position'], row['arm'])
        if isinstance(row['score'], bool) or not math.isfinite(float(row['score'])):
            raise ValueError('nonfinite/invalid score: ' + str(key))
        item = by_id[row['id']]
        if any(row[k] != item[k] for k in ('split', 'family')) or row['dispreferred'] != (row['prefilled'] != item['preferred']):
            raise ValueError('label/identity changed: ' + str(key))
        if not isinstance(row.get('outputs'), dict) or not row['outputs']:
            raise ValueError('empty outputs: ' + str(key))


def paths(out: str | Path, *, smoke: bool = False) -> dict[str, Path]:
    root = Path(out)/'smoke' if smoke else Path(out)
    return {key: root/value for key, value in OUTPUT_PATHS.items()}


def output_path(out: str | Path, key: str, *, smoke: bool = False) -> Path:
    if key not in OUTPUT_PATHS:
        raise ValueError('unregistered output path: ' + key)
    return paths(out, smoke=smoke)[key]


def audit_paths(out: str | Path) -> None:
    allowed = set(paths(out).values()) | set(paths(out, smoke=True).values())
    for file in Path(out).rglob('*'):
        if file.is_file() and file not in allowed:
            raise ValueError('unregistered output file: ' + str(file))


def stamp_row(row: Mapping[str, Any], *, run_id: str, run_kind: str, code_sha256: str) -> dict[str, Any]:
    if not run_id or run_kind not in ('real', 'smoke', 'test') or re.fullmatch(r'[0-9a-f]{64}', code_sha256) is None:
        raise ValueError('invalid run provenance')
    return dict(row) | {'run_id': run_id, 'run_kind': run_kind, 'code_sha256': code_sha256}


def audit_provenance(rows: Sequence[Mapping[str, Any]], *, run_kind: str | None = None) -> None:
    identities = set()
    for row in rows:
        name = str((row.get('id', 'receipt'), row.get('prefilled'), row.get('position'), row.get('arm')))
        if not row.get('run_id') or row.get('run_kind') not in ('real', 'smoke', 'test') or re.fullmatch(r'[0-9a-f]{64}', str(row.get('code_sha256', ''))) is None:
            raise ValueError('invalid provenance row: ' + name)
        if run_kind is not None and row['run_kind'] != run_kind:
            raise ValueError('wrong run kind row: ' + name)
        identities.add((row['run_id'], row['run_kind'], row['code_sha256']))
    if len(identities) > 1:
        raise ValueError('mixed run provenance; retain source provenance then use explicit aggregate stamp')


def validate_guard_receipt(receipt: Mapping[str, Any], *, own_pod_id: str, now: float,
                           expected_source_hashes: Mapping[str, str], phase: str) -> None:
    """Pure validation; actual API/SSH/PID checks belong to shared Mac tooling."""
    if phase not in PHASES or receipt.get('phase') != phase or receipt.get('brief_section') != BRIEF_SECTION:
        raise ValueError('assigned section/phase mismatch')
    if not own_pod_id or receipt.get('pod_id') != own_pod_id or not receipt.get('status_id_matched'):
        raise ValueError('own pod ID mismatch')
    if receipt.get('status_http') != 200:
        raise ValueError('own-pod status 200 check missing')
    pids = receipt.get('guard_pids', [])
    if receipt.get('guard_location') != 'mac' or len(pids) != 2 or len(set(pids)) != 2 or any(type(p) is not int or p <= 0 for p in pids):
        raise ValueError('two distinct Mac guards required')
    if receipt.get('guards_live') is not True:
        raise ValueError('live Mac guard verification missing')
    assigned, deadline = receipt.get('assigned_at'), receipt.get('hard_deadline')
    if not isinstance(assigned, (int, float)) or not isinstance(deadline, (int, float)) or not 0 < deadline-assigned <= MAX_SECONDS:
        raise ValueError('immutable 2.5-hour cap invalid')
    if not assigned <= now < deadline-PULL_RESERVE_SECONDS:
        raise ValueError('science cutoff; pull reserve begins')
    actual = receipt.get('source_hashes', {})
    if not expected_source_hashes or actual != dict(expected_source_hashes):
        bad = sorted(k for k in set(actual) | set(expected_source_hashes) if actual.get(k) != expected_source_hashes.get(k))
        raise ValueError('frozen source hashes changed: ' + repr(bad))
