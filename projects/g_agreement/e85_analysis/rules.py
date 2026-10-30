"""§199 E85 / §202 / §205: whole-matched-quartet bootstrap, primary(a) only."""
import numpy as np
from common.stats import wilson
from projects.g_agreement.understand.wmech2.core import require
DRAWS,SEED=5000,0
CELLS=((0,0),(0,1),(1,0),(1,1))

def means(x,axis):
    n=np.isfinite(x).sum(axis=axis)
    return np.divide(np.nansum(x,axis=axis),n,out=np.full(np.shape(n),np.nan),where=n>0)

def estimate(point,draws):
    return dict(estimate=float(point) if np.isfinite(point) else None,CI95=np.quantile(draws,[.025,.975]).tolist() if np.isfinite(draws).all() else None)

def contrasts(p):
    g=(p[...,2]+p[...,3]-p[...,0]-p[...,1])/2
    a=(p[...,1]+p[...,3]-p[...,0]-p[...,2])/2
    return dict(genre=g,addressed=a,genre_minus_addressed=g-a)

def summarize(rows,field):
    """One record per reader and cell, all four records of a matched set sampled together."""
    groups=sorted({x['matched_set'] for x in rows},key=str)
    mapping={(x['matched_set'],x['genre'],x['addressed']):x for x in rows}
    require(len(mapping)==len(rows),'duplicate matched-set cell')
    require(len(rows)==4*len(groups),'full matched quartets required')
    v=np.array([[mapping[(g,*c)][field] for c in CELLS] for g in groups],float)
    ix=np.random.default_rng(SEED).integers(0,len(groups),(DRAWS,len(groups)))
    p=means(v,0);draws=means(v[ix],1);pc,dc=contrasts(p),contrasts(draws)
    out=dict(cells={},effects={k:estimate(pc[k],dc[k]) for k in pc},matched_sets=len(groups))
    for j,(genre,addressed) in enumerate(CELLS):
        kept=int(np.isfinite(v[:,j]).sum());yes=int(np.nansum(v[:,j]))
        _,lo,hi=wilson(yes,kept)
        out['cells'][f'genre={genre},addressed={addressed}']=dict(estimate(p[j],draws[:,j]),total=len(groups),kept=kept,missing=len(groups)-kept,yes=yes,Wilson95=[lo,hi] if kept else None)
    return out

def verdict(effects,probe):
    g=effects['genre']['estimate'];a=effects['addressed']['estimate'];d=effects['genre_minus_addressed'];ci=d['CI95']
    gate=None if probe is None else probe>=.90
    if gate is not True or g is None or a is None or d['estimate'] is None or ci is None:
        rule='NOT EVALUABLE'
    else:rule='MET' if round(g,12)>=.20 and round(d['estimate'],12)>=.15 and ci[0]>0 else 'NOT MET'
    observed=None if g is None or a is None else a>=g
    return dict(R_E1=rule,addressed_probe_AUROC=probe,addressed_probe_gate=gate,
                falsifier='NOT EVALUABLE' if gate is not True or observed is None else 'MET' if observed else 'NOT MET',
                addressed_ge_genre_observed=observed)

def analyze(rows,probes,bow,behaviour):
    out=dict(experiment='E85',authority='§199 E85 with §202/§205; §211 amendment3 unchanged',bootstrap=dict(draws=DRAWS,seed=SEED,unit='matched quartet',paired_cells=True),readers={},probes=probes,BOW_descriptive=bow,behaviour_descriptive=behaviour)
    for reader,layer in (('oracle',44),('nla',42)):
        xs=sorted([x for x in rows if x['reader']==reader],key=lambda x:x['id'])
        primary=summarize(xs,'a');b=summarize(xs,'b');c=summarize(xs,'c')
        probe=next(x for x in probes if x['name']=='addressed' and x['layer']==layer)
        auroc=probe.get('test_auroc') if probe['status']=='COMPLETE' else None
        # Same subset for original/current comparison; other rows remain masked,
        # retaining the quartet design. Unselected rows are not judge failures.
        subset=[dict(x,a=x['a'] if x['original_selected'] else None) for x in xs]
        original=summarize(xs,'original');current=summarize(subset,'a')
        out['readers'][reader]=dict(primary_a=primary,genre_vocabulary_b=b,absent_genre_c=c,
            original_rubric=dict(selected=sum(x['original_selected'] for x in xs),selected_missing=sum(x['original_selected'] and x['original'] is None for x in xs),masked_not_selected=sum(not x['original_selected'] for x in xs),original=original,current_same_subset=current,missing_count_note='Tables include unselected masked rows; selected_missing counts actual failed original judgments.'),
            rules=verdict(primary['effects'],auroc),confirmatory=reader=='oracle')
    return out
