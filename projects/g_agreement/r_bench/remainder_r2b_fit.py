"""Manifest-bound on-volume probe fitting; no model or judge calls."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from projects.g_agreement.r_bench import remainder_r2b as D, remainder_r2b_runner as R, remainder_r2b_probe as P


def read_process(root, expected_kind='real'):
    root=Path(root).resolve()
    manifest=json.loads((root/'volume_manifest.json').read_text())
    process=json.loads((root/'process.json').read_text())
    if process['run_kind']!=expected_kind:
        raise ValueError(f'Wrong process kind: {process["run_kind"]}')
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}-{'volume_manifest.json'}
    if actual!=set(manifest['files']):
        raise ValueError(f'Process inventory differs: {sorted(actual^set(manifest["files"]))}')
    for name,want in manifest['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or R.sha(path)!=want:
            raise ValueError(f'Changed/unsafe process member: {name}')
    rows={}
    for line in (root/'rows.jsonl').read_text().splitlines():
        row=json.loads(line);key=row['cell_key']
        if key in rows:raise ValueError(f'Duplicate captured cell: {key}')
        if key!=D.digest(row['cell']):raise ValueError(f'Changed captured cell: {key}')
        for k,v in process.items():
            if row.get(k)!=v:raise ValueError(f'Wrong provenance {k}: {key}')
        rows[key]=(root,row)
    return rows


def load_tap(record,block):
    root,row=record;entry=row['state_files'].get(str(block))
    if entry is None:raise ValueError(f'Missing tap {block}: {row["cell_key"]}')
    path=(root/entry['path']).resolve()
    if not path.is_relative_to(root) or R.sha(path)!=entry['sha256']:
        raise ValueError(f'Changed/unsafe tap: {entry["path"]}')
    x=np.load(path,allow_pickle=False)
    if x.ndim!=1 or x.dtype!=np.float16 or not np.isfinite(x).all():
        raise ValueError(f'Invalid compact tap: {entry["path"]}')
    return x.astype(np.float32)


def fit_jobs(jobs,records,guard):
    """Jobs specify pool and evaluation cell keys, never fit on evaluation rows.

    Groups and labels are read from the captured selection cells. Control rows
    share the real-state fit; no separate fit on rebuilt or held-out states.
    """
    fits=[];predictions=[];seen=set()
    for job in jobs:
        guard();name=job['job_id']
        print(f'PROBE START {name}',flush=True)
        if name in seen:raise ValueError(f'Duplicate probe job: {name}')
        seen.add(name);train=job['train'];test=job['evaluate'];block=job['block']
        if not train or not test:raise ValueError(f'Empty probe partition: {name}')
        if len(set(train))!=len(train) or len(set(test))!=len(test):
            raise ValueError(f'Duplicate partition cell: {name}')
        if set(train)&set(test):raise ValueError(f'Train/evaluation overlap: {sorted(set(train)&set(test))}')
        for key in train+test:
            if key not in records:raise ValueError(f'Missing probe input: {key}')
        cells=[records[k][1]['cell'] for k in train]
        for key,cell in zip(train,cells):
            if cell['split']!='pool' or cell['arm']!='natural':
                raise ValueError(f'Non-pool/natural training cell: {key}')
        evaluation=[records[k][1]['cell'] for k in test]
        groups=[c['probe_group'] for c in cells]
        test_groups=[c['probe_group'] for c in evaluation]
        x=np.stack([load_tap(records[k],block) for k in train])
        fit_fn=P.fit_fixed_transfer if job.get('selection')=='forward-block transfer' else P.fit_pool
        fit=fit_fn(x,[c['label'] for c in cells],groups,test_groups)
        fit.update(job_id=name,block=block,train_cells=train,evaluation_cells=test)
        fits.append(fit)
        scores,labels=P.predict(fit,np.stack([load_tap(records[k],block) for k in test]))
        from sklearn.metrics import roc_auc_score
        y_test=[c['label'] for c in evaluation]
        descriptive_auc=float(roc_auc_score(y_test,scores)) if set(y_test)=={0,1} else None
        for key,cell,score,pred in zip(test,evaluation,scores,labels):
            predictions.append(dict(job_id=name,cell_key=key,block=block,
                item_id=cell['item_id'],dataset=cell['dataset'],arm=cell['arm'],
                label=cell['label'],score=float(score),prediction=int(pred),descriptive_job_auroc=descriptive_auc))
        print(f'PROBE COMPLETE {name}',flush=True)
    return fits,predictions
