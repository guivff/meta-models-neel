"""The narrowed §36 Oracle ablation slice; explicit, data-derived inventories."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import json
import numpy as np
from projects.g_agreement.r_bench import remainder_r2b as D,remainder_r2b_runner as R

ARMS=('sham','mean_ablation','random_ablation')


def entity_groups(items):
    """Connected entity/partner components, so a named person never crosses folds."""
    parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    for it in items:
        a=find(it['entity']);b=find(it.get('planted',{}).get('partner',it['entity']))
        parent[a]=b
    components=defaultdict(list)
    for name in parent:components[find(name)].append(name)
    names={root:D.digest(sorted(members)) for root,members in components.items()}
    return {it['item_id']:names[find(it['entity'])] for it in items}


def fact_components(items):
    parent={i['dataset']:i['dataset'] for i in items};texts={}
    def find(x):
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    for item in items:
        text=item.get('prompt_text')
        if text is None:continue
        ds=item['dataset']
        if text in texts:parent[find(ds)]=find(texts[text])
        else:texts[text]=ds
    groups=defaultdict(list)
    for ds in parent:groups[find(ds)].append(ds)
    return {ds:min(members) for members in groups.values() for ds in members}


def fold_map(items,nfold=5):
    """Keep shared-document fact components whole; balance difficulty and size."""
    components=fact_components(items);bins={i['dataset']:i['difficulty_bin'] for i in items}
    groups=defaultdict(list)
    for ds,component in components.items():groups[component].append(ds)
    loads=[0]*nfold;bin_loads=[defaultdict(int) for _ in range(nfold)];mapping={}
    for component,names in sorted(groups.items(),key=lambda kv:(-len(kv[1]),D.rank(kv[0]))):
        fold=min(range(nfold),key=lambda k:(loads[k],sum(bin_loads[k][bins[n]] for n in names),k))
        for ds in names:mapping[ds]=fold;bin_loads[fold][bins[ds]]+=1
        loads[fold]+=len(names)
    if set(mapping.values())!=set(range(nfold)):raise ValueError(f'Missing fact folds: {mapping}')
    return mapping


def capture_cells(items,depth):
    out=[];groups={}
    main_groups=fact_components([i for i in items if i['population']=='main'])
    byds=defaultdict(list)
    for it in items:
        if it['population']=='taught':byds[it['dataset']].append(it)
    for ds,rows in byds.items():groups.update(entity_groups(rows))
    for it in items:
        cell=dict(item_id=it['item_id'],dataset=it['dataset'],population=it['population'],
            recipe=it['recipe'],split=it['split'],label=it['label'],
            probe_group=main_groups[it['dataset']] if it['population']=='main' else groups[it['item_id']],
            reader='olens',arm='natural',item=it,state_paths=it['state_paths'],
            state_row=it['state_row'],tap_blocks=list(D.tap_blocks(depth)),generate=False)
        out.append(cell)
    if len({c['item_id'] for c in out})!=len(out):raise ValueError('Duplicate capture item_id')
    return out


def probe_jobs(cells,items):
    folds=fold_map([i for i in items if i['population']=='main']);cohorts={}
    for fold in sorted(set(folds.values())):
        train=[c for c in cells if c['population']=='main' and c['split']=='pool' and folds[c['dataset']]!=fold]
        test=[c for c in cells if c['population']=='main' and c['split']=='test' and folds[c['dataset']]==fold]
        cohorts[f'main-fold{fold}']=(train,test)
    for ds in sorted({c['dataset'] for c in cells if c['population']=='taught'}):
        cohorts[ds]=([c for c in cells if c['dataset']==ds and c['split']=='pool'],
                     [c for c in cells if c['dataset']==ds and c['split']=='test'])
    jobs=[];unsupported=[]
    for name,(train,test) in cohorts.items():
        # Fail before any paid capture if the preregistered grouped CV is impossible.
        from projects.g_agreement.r_bench.remainder_r2b_probe import grouped_splits
        try:grouped_splits([c['label'] for c in train],[c['probe_group'] for c in train]);supported=True
        except ValueError:supported=False
        if not supported:
            if '_rev@' not in name:raise ValueError(f'Unsupported primary training fold: {name}')
            unsupported.append(dict(cohort=name,reason='no valid group-disjoint two-label inner folds',
                selection='forward-block transfer',forward_cohort=name.replace('_rev@','_fwd@'),
                train=[R.cell_key(c) for c in train],evaluate=[R.cell_key(c) for c in test]))
            continue
        for block in train[0]['tap_blocks']:
            jobs.append(dict(job_id=f'{name}:block{block}',cohort=name,block=block,
                train=[R.cell_key(c) for c in train],evaluate=[R.cell_key(c) for c in test]))
    return jobs,unsupported


def select_fits(fits,jobs):
    expected={j['job_id']:j for j in jobs}
    if {f['job_id'] for f in fits}!=set(expected):
        raise ValueError(f'Probe fit coverage differs: {sorted({f["job_id"] for f in fits}^set(expected))}')
    groups=defaultdict(list)
    for fit in fits:
        job=expected[fit['job_id']]
        if fit['train_cells']!=job['train'] or fit['evaluation_cells']!=job['evaluate']:
            raise ValueError(f'Fit partition changed: {fit["job_id"]}')
        groups[job['cohort']].append(fit)
    return {name:min(values,key=lambda f:(-f['pool_validation_accuracy'],f['block'])) for name,values in groups.items()}


def causal_cells(selected,captured):
    bykey={R.cell_key(c):c for c in captured};out=[]
    for cohort,fit in sorted(selected.items()):
        u=np.asarray(fit['raw_normal']);seed=int(D.rank(cohort)[:16],16)
        rng=np.random.default_rng(seed);v=rng.normal(size=u.shape);v-=u*(v@u)
        if np.linalg.norm(v)<1e-12:raise ValueError(f'Degenerate random direction: {cohort}')
        v/=np.linalg.norm(v)
        for key in fit['evaluation_cells']:
            if key not in bykey:raise ValueError(f'Unknown evaluation cell: {key}')
            source=bykey[key]
            if source['split']!='test':raise ValueError(f'Non-test causal item: {source["item_id"]}')
            for arm in ARMS:
                cell=dict(source,arm=arm,cohort=cohort,fit_sha256=D.digest(fit),selection=fit.get('selection','pool-selected'))
                if arm!='sham':
                    cell['ablation']=dict(selected=fit['block'],mean=fit['mean'],
                        normal=(u if arm=='mean_ablation' else v).tolist())
                    if arm=='random_ablation':cell['ablation']['magnitude_normal']=u.tolist()
                out.append(cell)
    return out


def transfer_jobs(transfers,selected,blocks=None):
    jobs=[]
    for t in transfers:
        forward=t['forward_cohort']
        if forward not in selected:raise ValueError(f'Missing forward selection: {forward}')
        block=selected[forward]['block']
        for tap in (blocks if blocks is not None else [block]):
            jobs.append(dict(job_id=f"{t['cohort']}:transfer:block{tap}",cohort=t['cohort'],block=tap,
                train=t['train'],evaluate=t['evaluate'],selection='forward-block transfer',
                selected_for_causal=tap==block,forward_fit_sha256=D.digest(selected[forward])))
    return jobs


def validate_plan(plan):
    if plan.get('scope')!='ablation_slice':raise ValueError(f'Unsupported scope: {plan.get("scope")}')
    items=[c['item'] for c in plan['cells']]
    expected=capture_cells(items,plan['decoder_depth'])
    if plan['cells']!=expected:raise ValueError('Capture cells differ from derived selection')
    jobs,transfers=probe_jobs(expected,items)
    if plan['probe_jobs']!=jobs or plan['transfer_jobs']!=transfers:
        raise ValueError('Probe jobs differ from derived split/selection')
    if plan['code_sha256']!=D.code_sha256():raise ValueError(f'Execution code hash mismatch: {plan["code_sha256"]}')
    required={p for c in expected for p in c['state_paths'].values()}
    if required-set(plan['input_files']):raise ValueError(f'Unbound input states: {sorted(required-set(plan["input_files"]))}')
    receipt=json.loads((Path(__file__).resolve().parents[3]/'results/g_agreement/r/remainder/r2b/slice_input_receipt.json').read_text())
    if D.digest(expected)!=receipt['capture_cells_sha256']:raise ValueError('Capture selection differs from frozen slice input receipt')
    if D.digest(jobs)!=receipt['probe_jobs_sha256']:raise ValueError('Probe jobs differ from frozen slice input receipt')
    for path,record in receipt['source_files'].items():
        if plan['input_files'].get(path)!=record:raise ValueError(f'Source provenance differs from frozen receipt: {path}')
    return plan
