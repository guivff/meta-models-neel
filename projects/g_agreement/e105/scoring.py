"""Reader-free supplied-vector scoring adapter; model loading/custody belongs to Q."""
import math
import numpy as np
from . import frozen_e101_acquisition as E101
from .frozen_unpatched import plain_behaviour


def batches(items,size=8):
    """Use original unpadded E101 strata, separating true unpatched baselines."""
    for baseline in (False,True):
        indices=[i for i,x in enumerate(items) if (x['condition']=='0')==baseline]
        for group in E101.batches([items[i] for i in indices],size):yield [indices[j] for j in group]


def score_batch(model,items,vectors):
    if not items or {x['block'] for x in items}!={44}:raise ValueError('E105 block44')
    baseline={x['condition']=='0' for x in items}
    if len(baseline)!=1:raise ValueError('separate patched/unpatched batches')
    if True in baseline:
        if any(x['vector_index'] is not None or x['donor_id'] is not None for x in items):raise ValueError('unpatched baseline has no supplied state')
        results=plain_behaviour(model,items)
    else:
        if any(x['condition'] not in ('T','S') or type(x['vector_index'])is not int for x in items):raise ValueError('supplied T/S states')
        h=np.asarray(vectors)[[x['vector_index'] for x in items]].copy();before=h.tobytes()
        results=E101.behaviour(model,items,h,'continuation')
        if h.tobytes()!=before:raise ValueError('supplied residual mutated')
    if len(results)!=len(items):raise ValueError('exact result alignment')
    output=[]
    for x,r in zip(items,results):
        pairs=r['pair_logprobs']
        if len(pairs)!=len(x['candidate_ids']) or any(len(p)!=2 or any(not math.isfinite(v) for v in p) for p in pairs):raise ValueError('finite full continuation scores')
        output.append(dict(id=x['id'],inventory_id=x['inventory_id'],base_id=x['base_id'],row=x['row'],
            condition=x['condition'],block=44,vector_index=x['vector_index'],pair_logprobs=pairs))
    if len(output)!=len(items):raise ValueError('exact result alignment')
    return output
