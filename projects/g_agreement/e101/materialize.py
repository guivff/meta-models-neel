"""CPU-only composition. Signed deltas and truth keys never enter pod files."""
import hashlib
from pathlib import Path
import numpy as np
from .contract import DOSES,ROWS,read,write,sha,validate,committed_dose


def compose(records,carriers,directions,raw_norms,randoms,stage,*,repo=None,dose_path=None,dose_commit=None,dose_sha=None,ruling_commit):
    """Owner adapter supplies verified arrays, frozen candidate tokens and CPU labels.

    records: id (opaque), row, split, ids, candidate_ids, label (class1 minus class0),
    contrast_target_sign (opposite truth in frozen A-minus-B score orientation).
    carriers[(row,block)][id]; directions[(row,block)] unit; norms raw dev difference.
    Random direction is one fixed unit per block, supplied by the vector owner.
    """
    selected=None
    if stage=='test':
        receipt=committed_dose(repo,dose_path,dose_commit,dose_sha)
        if receipt['experiment']!='E101' or receipt['dev_count']!=84 or receipt['dose_policy']!='independent_blocks' or receipt['scoring_mode']!='continuation':raise ValueError('registered dev receipt')
        selected=receipt['selected_doses']
    elif stage!='dev':raise ValueError('dev or test stage')
    items=[];vectors=[];cpu_key={}
    for row in sorted({x['row'] for x in records}):
        if row not in ROWS:raise ValueError('registered row')
        xs=[x for x in records if x['row']==row and x['split']==stage]
        if len(xs)!=84 or len({x['id'] for x in xs})!=84:raise ValueError('84 frozen items per row/split')
        for block in (44,42):
            key=(row,block)
            alphas=DOSES if stage=='dev' else [selected[f'{row}:{block}']['alpha']]
            if alphas==[None]:continue
            unit=np.asarray(directions[key],np.float64);random=np.asarray(randoms[block],np.float64);norm=raw_norms[key]
            if unit.shape!=(5120,) or random.shape!=(5120,) or not np.isfinite(norm) or norm<=0 or not all(np.isfinite(v).all() and np.isclose(np.linalg.norm(v),1.,atol=1e-6) for v in (unit,random)):
                raise ValueError('sealed finite unit directions and dev norm')
            for x in xs:
                if x['label'] not in (0,1) or x['contrast_target_sign'] not in (-1,1):raise ValueError('CPU binary class and contrast orientation')
                h=np.asarray(carriers[key][x['id']],np.float64)
                if h.shape!=(5120,) or not np.isfinite(h).all() or np.linalg.norm(h)==0:raise ValueError('sealed carrier')
                cpu_key[x['id']]={k:x[k] for k in ('row','split','label','contrast_target_sign')}
                for a in alphas:
                    for condition in (('steered',) if stage=='dev' else ('steered','random')):
                        hp=(h+a*norm*(1-2*x['label'])*(unit if condition=='steered' else random)).astype(np.float32)
                        identity=hashlib.sha256(f'E101:{stage}:{row}:{block}:{x["id"]}:{a}:{condition}'.encode()).hexdigest()
                        items.append(dict(id=identity,base_id=x['id'],row=row,block=block,alpha=a,condition=condition,vector_index=len(vectors),
                            ids=x['ids'],read_index=len(x['ids'])-1,candidate_ids=x['candidate_ids'],norm_ratio=float(np.linalg.norm(hp.astype(np.float64))/np.linalg.norm(h))))
                        vectors.append(hp)
    if not vectors: return [],np.empty((0,5120),np.float32),cpu_key,selected
    h=np.stack(vectors);validate(items,h,stage,84,selected)
    return items,h,cpu_key,selected


def save(out,items,h,stage,selected,ruling_commit,owner_seal_sha256,dose_commit=None,dose_sha=None):
    if not items:raise ValueError('No evaluable rows; record NOT EVALUABLE on CPU, no pod package')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    write(out/'items.json',items);np.save(out/'vectors.npy',h,allow_pickle=False)
    write(out/'MANIFEST.json',dict(experiment='E101',status='FROZEN_READY',stage=stage,dev_count=84,dose_policy='independent_blocks',
        scoring_mode='continuation',ruling_commit=ruling_commit,authority=['69f8c08e4','2bdde763'],full_continuation_authority='direct user ruling: Full frozen continuation contrast',
        selected_doses=selected,dose_commit=dose_commit,dose_sha256=dose_sha,owner_seal_sha256=owner_seal_sha256))
    write(out/'INPUT_SEAL.json',dict(experiment='E101',labels_on_pod=False,files={p.name:sha(p) for p in out.iterdir() if p.is_file()}))
