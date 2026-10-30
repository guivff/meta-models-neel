"""Literal custody projection of generated tokens; no scoring or decoding."""
from copy import deepcopy

def project(token_ids, norm_trace, eos_ids):
    if not token_ids or any(type(x) is not int for x in token_ids):
        raise ValueError('original integer token IDs required')
    if not eos_ids or any(type(x) is not int for x in eos_ids):
        raise ValueError('source-bound EOS IDs required')
    stop=next((i+1 for i,x in enumerate(token_ids) if x in eos_ids),len(token_ids))
    # Prefill selects token0. A cached hook at position j processes token j
    # to select token j+1; EOS itself is not processed within the live sequence.
    count=max(0,stop-1)
    if len(norm_trace)<count or any(x['generated_position']!=i for i,x in enumerate(norm_trace)):
        raise ValueError('original contiguous hook-position trace required')
    return dict(token_ids=list(token_ids[:stop]),norm_trace=deepcopy(norm_trace[:count]),
                original_token_count=len(token_ids),generated_token_count=stop,
                original_trace_count=len(norm_trace),generated_trace_count=count,
                projection='literal first-EOS-inclusive token prefix; literal pre-EOS processed-token hook prefix')
