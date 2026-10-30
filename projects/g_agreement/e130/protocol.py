"""Port of exp24 lib24 token helpers; source23d5a972, seed overridden only by §237."""
import random
SEED = 20261031
MAX_TEXT_TOKENS = 256
SPAN_TOKENS = 32
EMPTY = '(empty)'


def shuffle_tokens(ids: list[int], rng: random.Random) -> list[int]:
    """The same tokens in a random order (structure broken, vocabulary kept)."""
    out = list(ids)
    for _ in range(10):
        rng.shuffle(out)
        if out != list(ids):
            break
    return out


def _readout_ids(text, tok_encode, cap):
    return tok_encode((text or '').strip() or EMPTY)[:cap]


def token_rows(dev, test, encode):
    """Three registered conditions only. One seeded stream in sealed TEST order."""
    rng = random.Random(SEED)
    rows = [dict(id=x['id'], split='dev', condition='span_32', ids=x['ids']) for x in dev]
    for x in test:
        ids = _readout_ids(x['text'], encode, MAX_TEXT_TOKENS)
        rows.append(dict(id=x['id'], split='test', condition='ol_readout', ids=ids))
        rows.append(dict(id=x['id'], split='test', condition='ol_readout_shuffled', ids=shuffle_tokens(ids, rng)))
    return rows
