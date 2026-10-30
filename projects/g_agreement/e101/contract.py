"""CPU custody, dose selection, and strict public-input schema for E101."""
import hashlib,json,math,subprocess
from pathlib import Path
import numpy as np
ROWS={'language_plan','format_plan','fact_recall','language_continuation','nesting_depth','indent_level','page_range_digit'}
DOSES=(.5,1.,2.,4.)
FIELDS={'id','base_id','row','block','alpha','condition','vector_index','ids','read_index','candidate_ids','norm_ratio'}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def write(p,x):
    with Path(p).open('x') as f: json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def verify(root,name,digest):
    root=Path(root).resolve();p=root/name
    if sha(p)!=digest: raise ValueError('seal identity')
    s=read(p)
    for name,h in s['files'].items():
        q=(root/name).resolve()
        if not q.is_relative_to(root) or sha(q)!=h: raise ValueError('sealed member identity')
    return s


def validate(items,h,stage,dev_count,selected=None):
    if stage not in ('dev','test') or type(dev_count)!=int or dev_count<1: raise ValueError('stage/count ruling')
    if not items or len({x['id'] for x in items})!=len(items): raise ValueError('unique nonempty cell IDs')
    if h.shape!=(len(items),5120) or h.dtype!=np.float32 or not np.isfinite(h).all(): raise ValueError('exact finite fp32 vectors')
    groups={}
    for i,x in enumerate(items):
        if set(x)!=FIELDS or x['vector_index']!=i or x['row'] not in ROWS or x['block'] not in (42,44): raise ValueError('public schema')
        if not x['ids'] or x['read_index']!=len(x['ids'])-1 or any(type(t)!=int or t<0 for t in x['ids']): raise ValueError('frozen prompt tokens')
        if not math.isfinite(x['norm_ratio']) or x['norm_ratio']<=0: raise ValueError('norm ratio')
        if x['alpha'] not in DOSES or x['condition'] not in (('steered',) if stage=='dev' else ('steered','random')): raise ValueError('registered cell')
        groups.setdefault((x['row'],x['block']),[]).append(x)
    for key,xs in groups.items():
        ids={x['base_id'] for x in xs};n=dev_count if stage=='dev' else 84
        if len(ids)!=n: raise ValueError('exact item count per row/block')
        alpha=DOSES if stage=='dev' else [selected[f'{key[0]}:{key[1]}']['alpha']]
        expected={(i,a,c) for i in ids for a in alpha for c in (('steered',) if stage=='dev' else ('steered','random'))}
        actual=[(x['base_id'],x['alpha'],x['condition']) for x in xs]
        if len(actual)!=len(set(actual)) or set(actual)!=expected: raise ValueError('complete registered dose/cell grid')
    return groups


def select(items,records,cpu_key,mode,dev_count):
    """Per-block smallest passing dose. Caller binds user ruling before use."""
    if mode not in ('next_token','continuation'): raise ValueError('scoring ruling')
    if len(records)!=len(items) or len({r['id'] for r in records})!=len(records) or {r['id'] for r in records}!={x['id'] for x in items}: raise ValueError('complete dev output grid')
    by={r['id']:r for r in records};groups={}
    for x in items:
        if x['condition']!='steered' or x['alpha'] not in DOSES: raise ValueError('dev only')
        k=cpu_key[x['base_id']]
        if k['split']!='dev' or k['row']!=x['row'] or k['contrast_target_sign'] not in (-1,1): raise ValueError('CPU dev label/orientation')
        pairs=by[x['id']]['pair_logits' if mode=='next_token' else 'pair_logprobs']
        if len(pairs)!=len(x['candidate_ids']) or any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in pairs): raise ValueError('finite frozen pair scores')
        contrast=float(np.mean([a-b for a,b in pairs]))
        groups.setdefault((x['row'],x['block']),{}).setdefault(x['alpha'],[]).append((x['base_id'],contrast*k['contrast_target_sign']>0))
    result={}
    for (row,block),ds in groups.items():
        if set(ds)!=set(DOSES): raise ValueError('all four doses required')
        ids=None;counts={}
        for a,vs in ds.items():
            current={i for i,_ in vs}
            if len(vs)!=dev_count or len(current)!=dev_count or (ids is not None and current!=ids): raise ValueError('same full dev set at every dose')
            ids=current;counts[str(a)]=sum(v for _,v in vs)
        chosen=next((a for a in DOSES if counts[str(a)]/dev_count>=.70),None)
        result[f'{row}:{block}']=dict(alpha=chosen,status='SELECTED' if chosen else 'NOT_EVALUABLE_NO_BEHAVIOURAL_FLIP',dev_n=dev_count,target_side_counts=counts)
    return result


def committed_dose(repo,path,commit,digest):
    """Test construction is forbidden until the exact dose bytes are committed."""
    repo=Path(repo).resolve();path=Path(path).resolve()
    rel=str(path.relative_to(repo))
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit): raise ValueError('full dose commit')
    blob=subprocess.check_output(['git','show',f'{commit}:{rel}'],cwd=repo)
    if hashlib.sha256(blob).hexdigest()!=digest or sha(path)!=digest: raise ValueError('committed dose identity')
    return json.loads(blob)


def policy_settings(policy):
    if policy!='clarification1':raise ValueError('latest registered policy only')
    return 84,'independent_blocks','continuation'
