"""§236 clarification4: frozen candidate parser; pair preference is descriptive only."""
import hashlib
import math
from pathlib import Path
from projects.g_agreement.core import analysis_utils

PARSER_SHA256 = 'cf6bc5edc904a688b4c292064f230cbb6feec0b9a437ed80ac3b7993396fc390'
# Exact E101/E104 fact_recall continuation strings; never inferred from outputs.
PAIR_STRINGS = ((' Paris', ' Lima'),)


def source_gate():
    if hashlib.sha256(Path(analysis_utils.__file__).read_bytes()).hexdigest() != PARSER_SHA256:
        raise ValueError('frozen candidate parser source changed')


def classify(text, old_value, new_value):
    """Return old/new/neither using parse_target_answer unchanged and no aliases."""
    source_gate()
    if not isinstance(text, str):
        raise ValueError('missing raw answer is not a neither answer')
    if any(not isinstance(v, str) or not v.strip() for v in (old_value, new_value)) or old_value.casefold() == new_value.casefold():
        raise ValueError('distinct sealed nonempty candidates')
    item = {'primary': {'candidates': [old_value, new_value], 'answer': old_value}}
    value = analysis_utils.parse_target_answer(item, text)
    return 'old' if value == old_value else 'new' if value == new_value else 'neither'


def pair_preference_flip(pair_logits, new_value):
    """Exact E104 mean(A-B)>0 toward target; no input to text classification."""
    if pair_logits is None:
        return None
    if len(pair_logits) != len(PAIR_STRINGS):
        raise ValueError('original E104 candidate count')
    contrasts = []
    for pair, names in zip(pair_logits, PAIR_STRINGS):
        if len(pair) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in pair):
            raise ValueError('finite original E104 pair logits')
        names = tuple(s.strip() for s in names)
        if new_value not in names:
            raise ValueError('sealed target must match original candidate string')
        sign = 1 if new_value == names[0] else -1
        contrasts.append((pair[0] - pair[1]) * sign)
    return sum(contrasts) / len(contrasts) > 0


def classify_record(record, binding):
    """Pure CPU wrapper; caller opens sealed outputs only after committed binding."""
    if record['id'] != binding['id'] or record.get('greedy_max_new_tokens') != 3:
        raise ValueError('exact original identity and registered three-token answer')
    ids = record.get('token_ids')
    if not isinstance(ids, list) or not 1 <= len(ids) <= 3 or any(type(t) is not int or t < 0 for t in ids):
        raise ValueError('original greedy token IDs, up to3 including early EOS')
    answer = classify(record['text'], binding['old_value'], binding['new_value'])
    return dict(id=record['id'], answer_value=answer, flipped=answer == 'new',
                pair_preference_flip_descriptive=pair_preference_flip(record.get('pair_logits'), binding['new_value']))
