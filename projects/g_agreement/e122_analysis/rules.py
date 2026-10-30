"""E105's paired bootstrap, re-pointed to matched E85 quartets."""
import numpy as np
from projects.g_agreement.e105_analysis.rules import statistic, DRAWS, SEED


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate_cells(cells):
    require(len(cells) == 600 and len({x['id'] for x in cells}) == 600, 'original 600 unique E85 cells')
    groups = {}
    for x in cells:
        require(x['split'] in ('dev','test') and type(x['genre']) is int and x['genre'] in (0,1)
                and type(x['addressed']) is int and x['addressed'] in (0,1), 'original E85 factors')
        groups.setdefault(x['quartet_id'], []).append(x)
    require(len(groups) == 150, '150 original matched quartets')
    for xs in groups.values():
        require(len(xs) == 4 and {(x['genre'],x['addressed']) for x in xs} == {(0,0),(0,1),(1,0),(1,1)}
                and len({x['split'] for x in xs}) == 1, 'complete quartet, split never leaks')
    require(sum(xs[0]['split'] == 'dev' for xs in groups.values()) == 50, '50 dev and 100 test quartets')
    return cells


def same_condition_pairs(cells):
    """Guiv clarification: same-value ADDRESSED S, exact frozen runner recipe."""
    validate_cells(cells)
    test=sorted({x['quartet_id'] for x in cells if x['split']=='test'})
    by={(x['quartet_id'],x['genre'],x['addressed']):x for x in cells}
    rng=np.random.default_rng(20261030)
    pairs=[]
    for genre in (0,1):
        permutation=[test[k] for k in rng.permutation(len(test))]
        donors={q:permutation[(k+1)%len(test)] for k,q in enumerate(permutation)}
        for q in test:
            carrier=by[q,genre,0];twin=by[q,genre,1];other=by[donors[q],genre,1]
            require(donors[q]!=q, 'same-value donor from another quartet')
            pairs.append(dict(id=carrier['id'],quartet_id=q,genre=genre,T_donor_id=twin['id'],S_donor_id=other['id']))
    return pairs


def quartet_differences(records, score_key, n, *, transplant=False):
    require(len(records) == n*(2 if transplant else 4) and len({x['id'] for x in records}) == len(records), 'complete unique measured cells')
    groups = {}
    for x in records:
        key = (x['quartet_id'],x['genre'])
        groups.setdefault(key, []).append(x)
    quartets = sorted({x['quartet_id'] for x in records})
    require(len(quartets) == n and len(groups) == 2*n, 'full paired quartet/genre inventory')
    genres = {0:[],1:[]}
    for quartet in quartets:
        for genre in (0,1):
            xs = groups.get((quartet,genre), [])
            if transplant:
                require(len(xs)==1 and xs[0]['addressed']==0, 'unaddressed transplant carrier')
                d = xs[0]['scores']['T']-xs[0]['scores']['S']
            else:
                require(len(xs)==2 and {x['addressed'] for x in xs}=={0,1}, 'matched addressed twin')
                by = {x['addressed']:x for x in xs}
                d = by[1]['scores'][score_key]-by[0]['scores'][score_key]
            require(np.isfinite(d), 'finite contrast; never drop a quartet')
            genres[genre].append(float(d))
    pooled = (np.asarray(genres[0])+np.asarray(genres[1]))/2
    return pooled, genres


def select_dev(records, contrast_order):
    require(len(contrast_order)==len(set(contrast_order))==4 and all(x['split']=='dev' for x in records), 'four frozen contrasts, dev only')
    require(all(set(x['scores'])==set(contrast_order) for x in records), 'all four dev scores')
    means = {c:float(np.mean(quartet_differences(records,c,50)[0])) for c in contrast_order}
    # max keeps the first frozen manifest entry on an exact numerical tie.
    selected = max(contrast_order, key=means.get)
    return dict(selected_contrast_id=selected,dev_mean_addressed_shift=means,contrast_order=contrast_order,
                n_dev_quartets=50,genres_pooled_within_quartet=2,tie_break='first frozen manifest entry',selection_metric='signed addressed minus unaddressed mean; not absolute shift')


def native_test(records, selected):
    require(all(x['split']=='test' and set(x['scores'])=={selected} for x in records), 'selected contrast only on test')
    shifts, genres = quartet_differences(records,selected,100)
    pooled = statistic(shifts)
    met = pooled['estimate']>0 and pooled['CI95'][0]>0
    return dict(experiment='E122',phase='native_test',selected_contrast_id=selected,n_test_quartets=100,
                bootstrap=dict(draws=DRAWS,seed=SEED,backend='E105 statistic/common.stats.py',unit='quartet',paired=True),
                native_addressed_shift=pooled,per_genre={str(k):statistic(v) for k,v in genres.items()},
                R_BEV1='MET' if met else 'NOT MET',transplant_disposition='ELIGIBLE' if met else 'NOT RUN',
                R_BEV2='PENDING CONDITIONAL TRANSPLANT' if met else 'NOT RUN',
                disposition_scope='analysis; sealed transplant acquisition may already exist under the cap note',
                reading='test the conditional transplant' if met else 'the explicit cue does not measurably change these behaviours')


def transplant(records, gate):
    require(gate['R_BEV1']=='MET' and gate['native_addressed_shift']['estimate']>0 and gate['native_addressed_shift']['CI95'][0]>0, 'conditional R-BEV1 gate')
    require(all(x['split']=='test' and set(x['scores'])=={'T','S'} for x in records), 'test T/S only')
    delta, genres = quartet_differences(records,None,100,transplant=True)
    pooled = statistic(delta)
    met = pooled['estimate']>0 and pooled['CI95'][0]>0
    denom = gate['native_addressed_shift']['estimate']
    return dict(experiment='E122',phase='transplant',selected_contrast_id=gate['selected_contrast_id'],
                n_test_quartets=100,bootstrap=gate['bootstrap'],delta=pooled,
                per_genre={str(k):statistic(v) for k,v in genres.items()},R_BEV2='MET' if met else 'NOT MET',
                fraction_recovered=dict(estimate=pooled['estimate']/denom,numerator=pooled['estimate'],denominator=denom,
                                        definition='pooled mean Delta / pooled mean native addressed shift',clipped=False),
                reading='read-site vector carries part of the evaluation-dependent behaviour' if met else 'behaviour change is carried at other positions or layers',
                rules_unchanged_from='§232',contrast_orientation='frozen A-minus-B for native,T,S; no donor-dependent reorientation')
