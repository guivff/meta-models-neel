"""E42 §151 clarification 1: undetermined extensions carry forward."""
def persistence(prefix_ids, following_ids, expected_label, decode, state, horizon=32):
    if horizon != 32 or len(following_ids) != horizon:
        raise ValueError('exactly 32 generated tokens required')
    initial = state(decode(list(prefix_ids)))
    if initial is None:return None
    if initial != expected_label:raise ValueError('determined state at k=0 disagrees with frozen label')
    previous = initial
    for k in range(1, horizon+1):
        current = state(decode(list(prefix_ids)+list(following_ids[:k])))
        if current is not None:previous=current
        if previous != expected_label:return k-1
    return horizon
