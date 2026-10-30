"""§213 public cells, per-arm dose policy, and CPU-only dev selection."""
import math
import numpy as np
from .contract import read,write,sha,verify,committed_dose
from .intervention104 import WRITE_BLOCK,write_positions,NORM_CONVENTION
ROWS=('fact_recall','language_plan')
DOSES={'N':(.5,1.,2.,4.),'U':(.5,1.,2.,4.,8.)}
SEED=20261029
FIELDS={'id','base_id','row','arm','block','alpha','condition','delta_index','ids','read_index','write_positions','candidate_ids'}


def validate(items,deltas,manifest,dimension=5120):
    stage=manifest['stage']
    if manifest['experiment']!='E104' or stage not in ('dev','test') or manifest['seed']!=SEED or manifest['dev_count']!=84:
        raise ValueError('registered E104 manifest')
    if manifest['dose_grids']!={a:list(v) for a,v in DOSES.items()} or manifest['dose_score_field']!='pair_logits' or manifest['scoring_mode']!='continuation':
        raise ValueError('frozen per-arm grids and scorer')
    if (manifest['U_hook']!=dict(block=40,positions='eight_before_read',read_token_untouched=True)
        or manifest['N_hook']!=dict(block=44,positions='read_token',renormalized=True,random_renormalized=True)
        or manifest['norm_convention']!=NORM_CONVENTION):raise ValueError('registered hook/norm provenance')
    if deltas.shape!=(len(items),dimension) or deltas.dtype!=np.float32 or not np.isfinite(deltas).all():raise ValueError('finite fp32 signed deltas')
    if not items or len({x['id'] for x in items})!=len(items):raise ValueError('unique nonempty cell IDs')
    groups={}
    for i,x in enumerate(items):
        if set(x)!=FIELDS or type(x['delta_index'])is not int or x['delta_index']!=i or x['row'] not in ROWS or x['arm'] not in DOSES:raise ValueError('public E104 fields only')
        if x['block']!=WRITE_BLOCK[x['arm']] or (type(x['alpha']) not in (int,float) or x['alpha'] not in DOSES[x['arm']]) or x['condition'] not in ('steered','random'):raise ValueError('registered E104 intervention')
        if not x['ids'] or x['read_index']!=len(x['ids'])-1 or any(type(t)is not int or t<0 for t in x['ids']):raise ValueError('frozen prompt tokens/read position')
        if x['write_positions']!=write_positions(x['arm'],[x['read_index']])[0]:raise ValueError('exact write sites, never read token in U')
        pairs=x['candidate_ids']
        if not pairs or any(len(p)!=2 or any(len(c)!=1 or type(c[0])is not int or c[0]<0 for c in p) for p in pairs):raise ValueError('E104 frozen one-token candidates')
        groups.setdefault((x['arm'],x['row']),[]).append(x)
    declared={(x['arm'],x['row']) for x in manifest['cells']}
    if set(groups)!=declared or len(declared)!=len(manifest['cells']):raise ValueError('exact declared arm/row cells')
    if stage=='test':validate_doses(manifest['selected_doses'])
    for (arm,row),xs in groups.items():
        ids={x['base_id'] for x in xs}
        if len(ids)!=84:raise ValueError('84 full frozen items per arm/row')
        doses=DOSES[arm] if stage=='dev' else [manifest['selected_doses'][f'{arm}:{row}']['alpha']]
        if None in doses:raise ValueError('no test cells for an ineligible arm/row')
        expected={(i,a,c) for i in ids for a in doses for c in ('steered','random')}
        observed=[(x['base_id'],x['alpha'],x['condition']) for x in xs]
        if len(observed)!=len(set(observed)) or set(observed)!=expected:raise ValueError('complete per-arm dose/condition grid')
    return groups


def validate_doses(selected):
    if set(selected)!={f'{a}:{r}' for a in DOSES for r in ROWS}:raise ValueError('all four arm/row dose receipts')
    for key,v in selected.items():
        grid=DOSES[key.split(':')[0]];counts=v['target_side_counts']
        if set(counts)!={str(a) for a in grid} or any(type(n)is not int or not 0<=n<=84 for n in counts.values()):raise ValueError('registered complete dev counts')
        chosen=next((a for a in grid if counts[str(a)]/84>=.70),None)
        if v['alpha']!=chosen:raise ValueError('smallest qualifying dose')


def select(items,records,key):
    if len(records)!=len(items) or len({r['id'] for r in records})!=len(records) or {r['id'] for r in records}!={x['id'] for x in items}:raise ValueError('complete unique dev outputs')
    by={r['id']:r for r in records};groups={}
    for x in items:
        k=key[x['base_id']]
        if k['split']!='dev' or k['row']!=x['row'] or k['contrast_target_sign'] not in (-1,1):raise ValueError('CPU dev target orientation')
        if (type(x['alpha']) not in (int,float) or x['alpha'] not in DOSES[x['arm']]):raise ValueError('arm-specific dose grid')
        pairs=by[x['id']]['pair_logits']
        if len(pairs)!=len(x['candidate_ids']) or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in pairs):raise ValueError('finite frozen candidate scores')
        if x['condition']!='steered':continue  # Validate but never use random outputs for dose choice.
        flip=float(np.mean([a-b for a,b in pairs]))*k['contrast_target_sign']>0
        groups.setdefault((x['arm'],x['row']),{}).setdefault(x['alpha'],[]).append((x['base_id'],flip))
    result={}
    for (arm,row),ds in groups.items():
        if set(ds)!=set(DOSES[arm]):raise ValueError('full arm-specific grid')
        baseline=None;counts={}
        for a,vs in ds.items():
            ids={i for i,_ in vs}
            if len(vs)!=84 or len(ids)!=84 or (baseline is not None and ids!=baseline):raise ValueError('same84dev items at every dose')
            baseline=ids;counts[str(a)]=sum(bool(v) for _,v in vs)
        alpha=next((a for a in DOSES[arm] if counts[str(a)]/84>=.70),None)
        result[f'{arm}:{row}']=dict(alpha=alpha,dev_n=84,status='SELECTED' if alpha is not None else 'NOT_EVALUABLE_NO_BEHAVIOURAL_FLIP',target_side_counts=counts)
    return result
