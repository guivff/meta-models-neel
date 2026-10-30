"""§251 whitened reconstruction-FVE PROXY, not a certified replay of training reward."""
import numpy as np

def whiten(raw,mu,w):
    x=np.asarray(raw,dtype=np.float32);mu=np.asarray(mu,dtype=np.float32);w=np.asarray(w,dtype=np.float32)
    if w.shape!=(len(mu),len(mu)) or x.shape[-1]!=len(mu) or not all(np.isfinite(z).all() for z in (x,mu,w)):raise ValueError('finite common-coordinate moments/vectors')
    return (x-mu)@w.T

def joint_proxy(white_vectors,white_target):
    """Released nnls_refit arithmetic: unit directions,80 projected-gradient steps."""
    v=np.asarray(white_vectors,dtype=np.float32);x=np.asarray(white_target,dtype=np.float32)
    if x.ndim!=1 or v.ndim!=2 or v.shape[1]!=len(x) or not np.isfinite(v).all() or not np.isfinite(x).all() or float(x@x)<=0:raise ValueError('finite nonzero target and compatible atom matrix')
    if not len(v):return 0.
    v=v/(np.linalg.norm(v,axis=1,keepdims=True)+np.float32(1e-9))
    gram=v@v.T;rhs=v@x;step=1./max(float(np.trace(gram)),1e-12);coef=np.zeros(len(v),dtype=np.float32)
    for _ in range(80):coef=np.maximum(coef-step*(gram@coef-rhs),0.)
    residual=x-coef@v
    return float(1.-float(residual@residual)/max(float(x@x),1e-12))

def whitened_fve(native_prediction,whitened_target):
    """E125/E130 output-coordinate convention; explicitly proxy, no fitted alignment."""
    p=np.asarray(native_prediction,dtype=np.float32);g=np.asarray(whitened_target,dtype=np.float32)
    if p.shape!=g.shape or p.ndim!=1 or not np.isfinite(p).all() or not np.isfinite(g).all() or float(g@g)<=0:raise ValueError('compatible finite native/target whitened vectors')
    return float(1.-float((p-g)@(p-g))/max(float(g@g),1e-12))


def joint_audit_four(base_vectors,true_vector,false_vector,neutral_vector,target):
    """No baseline bullets dropped when appending; each new phrase adds ONE atom."""
    base=np.asarray(base_vectors,dtype=np.float32);result={'original':joint_proxy(base,target)}
    for name,vec in [('true',true_vector),('false',false_vector),('neutral',neutral_vector)]:
        result[name]=joint_proxy(np.concatenate([base,np.asarray(vec,dtype=np.float32)[None]],axis=0),target)
    return result

def summarize(rows,draws=2000,seed=20261030):
    required={'nesting_depth','inside_string','table_column','language','fact_recall','evaluation_cue'}
    if {r['state'] for r in rows}!=required or len(rows)!=120 or len({r['id'] for r in rows})!=120:raise ValueError('exact sealed120items/sixstates')
    results={}
    for state in sorted(required):
        xs=[r for r in rows if r['state']==state]
        if len(xs)!=20:raise ValueError('exact20perstate')
        vals=np.array([[r['scores'][k] for k in ('original','true','false','neutral')] for r in xs],dtype=float)
        if not np.isfinite(vals).all():raise ValueError('complete finite scores, no imputation')
        rng=np.random.default_rng(seed);ix=rng.integers(0,20,size=(draws,20));stats={}
        for key,a,b in [('true_minus_neutral',1,3),('true_minus_false',1,2),('true_minus_original',1,0)]:
            delta=vals[:,a]-vals[:,b];stats[key]={'mean':float(delta.mean()),'CI95':list(map(float,np.quantile(delta[ix].mean(axis=1),[.025,.975])))}
        results[state]=stats
    gate=any(results[s]['true_minus_neutral']['CI95'][0]>0 for s in ('language','fact_recall'))
    return dict(experiment='E139',score_label='proxy reward',instrument_gate='PASS' if gate else 'NOT EVALUABLE (instrument)',structural_reading_allowed=gate,states=results,bootstrap=dict(unit='paired originalitem withinstate',draws=draws,seed=seed,refits=0),delta_u='PENDING_SEALED_SPAN_REBUILDS; see delta_u() and section251 clarification1')


def primary_four(predictions, target):
    """Each prediction is a rebuild of the entire original/appended string."""
    if set(predictions) != {'original', 'true', 'false', 'neutral'}:
        raise ValueError('four exact whole-string conditions required')
    return {name: whitened_fve(vector, target) for name, vector in predictions.items()}


def delta_u(dev_rebuilds, dev_labels, originals, appended, draws=2000, seed=20261030):
    """Section251 clarification1: class-gap fraction in native AR whitened space.

    Dev text-span rebuilds define the direction; readouts never fit it.
    Inputs are native AR outputs in ONE space, without extra normalization.
    Bootstrap original items, holding the dev-defined direction fixed.
    """
    dev = np.asarray(dev_rebuilds, dtype=np.float64)
    labels = np.asarray(dev_labels)
    base = np.asarray(originals, dtype=np.float64)
    if dev.ndim != 2 or labels.shape != (len(dev),) or set(labels.tolist()) != {0, 1}:
        raise ValueError('two nonempty frozen dev-span classes required')
    if base.ndim != 2 or base.shape[1] != dev.shape[1] or len(base) != 20:
        raise ValueError('20 original readout rebuilds in the same space required')
    if set(appended) != {'true', 'false', 'neutral'}:
        raise ValueError('true/false/neutral append rebuilds required')
    if not np.isfinite(dev).all() or not np.isfinite(base).all():
        raise ValueError('finite complete rebuilds required')
    gap = dev[labels == 1].mean(0) - dev[labels == 0].mean(0)
    norm = float(np.linalg.norm(gap))
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError('NOT EVALUABLE: zero/nonfinite dev class gap')
    direction = gap / norm
    rng = np.random.default_rng(seed)
    ix = rng.integers(0, len(base), size=(draws, len(base)))
    out = {}
    for name, values in appended.items():
        values = np.asarray(values, dtype=np.float64)
        if values.shape != base.shape or not np.isfinite(values).all():
            raise ValueError('complete paired appended rebuilds required')
        movement = (values - base) @ direction / float(gap @ direction)
        out[name] = {'mean': float(movement.mean()),
                     'CI95': list(map(float, np.quantile(movement[ix].mean(1), [.025, .975]))),
                     'per_item': list(map(float, movement))}
    return {'formula': 'mean(<AR(r+u)-AR(r),d>)/<m1-m0,d>',
            'space': 'native AR whitened output; no extra transform/alignment',
            'dev_class_counts': [int((labels == x).sum()) for x in (0, 1)],
            'dev_class_gap_norm': norm, 'conditions': out,
            'bootstrap': {'unit': 'original item', 'draws': draws, 'seed': seed,
                          'direction_refit': False}}
