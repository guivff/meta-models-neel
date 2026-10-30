"""Per-readout pass under each E80 family's pinned WorkspaceBench headline scorer (commit 86612fa4).

Ported from W-text's packaged reference sources (export_2026-10-28_v3/reference_data):
  basic (multihop, association, poetry): src/wsbench/basic/judge.py _verdict -> expressed AND quote_verified.
  chain_intermediates: src/wsbench/evals/chain_intermediates/judge.py verdict -> hit (verified top value in gold).
  multilingual_multihop: the CPU regex scorer's 'pass' (regex80.score_sample, run by the channel).
wsbench.mc.fold is not in the package; fold() follows its documented contract (case, accents and quotes folded).
A missing or UNPARSEABLE judgment returns None (missing), never a fail.
"""
import re
import unicodedata

MAX_VALUES = 3  # chain prompts.py
NEAR = 3
_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")
_QUOTES = str.maketrans({'‘': "'", '’': "'", '‚': "'", '‛': "'", '“': '"', '”': '"', '„': '"', '«': '"', '»': '"', '`': "'"})


def _bfold(s):
    s = _ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), s.lower())
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if c.isalnum() and not unicodedata.combining(c))


def _in_sample(quote, sample):
    if quote in sample:return True
    norm = ' '.join(quote.lower().split())
    if norm and norm in ' '.join(sample.lower().split()):return True
    folded = _bfold(quote)
    return bool(folded) and folded in _bfold(sample)


def quote_verified(quote, samples):
    return bool(quote.strip()) and any(_in_sample(quote, s) for s in samples)


def fold(s):
    s = unicodedata.normalize('NFKD', s.translate(_QUOTES))
    return ''.join(c for c in s if not unicodedata.combining(c)).casefold()


def quote_in(quote, text):
    q = fold(quote.strip())
    return bool(q) and q in fold(text)


def names_number(n, text):
    return re.search(rf"(?<!\d)(?<!\d\.){n}(?!\d)(?!\.\d)", text) is not None


def near_set(gold):
    out = set()
    for v in gold:
        out.update(x for x in range(max(1, v-NEAR), v+NEAR+1))
    return sorted(out-set(gold))


def chain_hit(res, gold, readout):
    raw = res.get('values')
    values = [int(v) for v in raw if isinstance(v, int) and not isinstance(v, bool)][:MAX_VALUES] if isinstance(raw, list) else []
    if not values:return False
    top = values[0];quote = str(res.get('quote', '')).strip()
    quote_ok = names_number(int(quote), readout) if quote.isdigit() else quote_in(quote, readout)
    return (names_number(top, readout) or quote_ok) and top in gold


def passed(record, packet, readout):
    """True/False under the family's headline scorer; None when the judgment is missing or UNPARSEABLE."""
    if record is None:return None
    status = record.get('status')
    if packet['headline_scorer'] == 'regex':
        if status != 'CPU_REGEX':return None
        return bool(record['result']['pass'])
    if status != 'KEPT' or not isinstance(record.get('result'), dict):return None
    res = record['result']
    if packet['headline_scorer'] == 'basic':
        return bool(res.get('expressed')) and quote_verified(str(res.get('quote') or ''), [readout])
    if packet['headline_scorer'] == 'chain':
        return chain_hit(res, [int(v) for v in packet['gold_intermediates']], readout)
    raise ValueError('unknown headline scorer: '+str(packet['headline_scorer']))
