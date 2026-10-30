"""Build R2-B frozen input selection from existing artifacts; no model calls."""
from __future__ import annotations
import csv,gzip,json
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
from projects.g_agreement.r_bench import remainder_r2b as D,remainder_r2b_runner as R


def read(path):return json.loads(Path(path).read_text())

def lines(path):
    with Path(path).open() as f:
        for line in f:
            if line.strip():yield json.loads(line)


def main_selection(bank,th3_csv,th3_manifest):
    frozen=read(th3_manifest)
    if R.sha(th3_csv)!=frozen['preprojection_sha256']:raise ValueError('TH-3 preprojection hash mismatch')
    margins=defaultdict(list); defects=set()
    with gzip.open(th3_csv,'rt') as f:
        for r in csv.DictReader(f):
            if str(r['label_defect']).lower() in ('true','1'):defects.add(r['dataset'])
            value=float(r['A'])
            if np.isfinite(value):margins[r['dataset']].append(abs(value))
    items=read(bank)['items'];groups=defaultdict(list)
    for it in items:groups[it['dataset']].append(it)
    facts=[];excluded=[]
    for ds,rows in sorted(groups.items()):
        if ds not in margins or ds in defects:continue
        try:
            if any(len(r['primary']['candidates'])!=2 or r['primary']['candidates'][0]==r['primary']['candidates'][1] for r in rows):
                raise ValueError('Invalid binary candidates')
            D.balanced_items(rows,'pool',64);D.balanced_items(rows,'test',16)
        except ValueError as e:
            excluded.append(dict(dataset=ds,reason=str(e)));continue
        facts.append(dict(dataset=ds,label_defect=False,binary=True,provenance_ok=True,
                          median_abs_model_margin=float(np.median(margins[ds]))))
    chosen=D.select_main(facts);selected=[]
    for fact in chosen:
        for split,n in [('pool',64),('test',16)]:
            for it in D.balanced_items(groups[fact['dataset']],split,n):
                selected.append(dict(it,population='main',difficulty_bin=fact['difficulty_bin'],recipe='base'))
    return dict(facts=chosen,items=selected,excluded=excluded,th3_sha256=R.sha(th3_csv),bank_sha256=R.sha(bank))


def verify_n6(finalization):
    finalization=Path(finalization);pub=read(finalization/'publication.json')
    for name,want in pub['members'].items():
        p=finalization/name
        if not p.resolve().is_relative_to(finalization.resolve()):raise ValueError(f'N6 unsafe path: {name}')
        if R.sha(p)!=want:raise ValueError(f'N6 changed member: {name}')
    quartets=list(lines(finalization/'cache/quartets.jsonl'))
    counts=Counter(q['stratum'] for q in quartets)
    if len(quartets)!=23 or counts.get('distinct_cue_primary')!=3:raise ValueError(f'N6 frozen quartet coverage: {counts}')
    ids=[i for q in quartets for i in q['items']]
    if len(ids)!=len(set(ids)):raise ValueError('N6 duplicate endpoints')
    for name in ('quartets.jsonl','readouts.jsonl'):
        for row in lines(finalization/'cache'/name):
            if row.get('run_kind')!='real':raise ValueError(f'N6 nonreal row: {name}')
    if pub['coverage']['missing']:raise ValueError('N6 missing logical dispositions')
    return dict(publication_sha256=R.sha(finalization/'publication.json'),
                members=pub['members'],quartets=quartets,coverage=pub['coverage'],
                test_ids=sorted(ids),pool_ids=sorted({i for q in quartets for i in q['training_ids']}))


def bind_states(items,source,layers=(42,44)):
    """Freeze every referenced matrix and its row/index mapping, not directory globs."""
    source=Path(source);inputs={};bound=[];cache={}
    for item in items:
        ds=item['dataset']
        if ds not in cache:
            p=source/ds/'index.json';idx=read(p)
            if idx.get('dataset')!=ds:raise ValueError(f'State dataset mismatch: {ds}')
            ids=idx['item_ids']
            if len(ids)!=len(set(ids)):raise ValueError(f'Duplicate state IDs: {ds}')
            inputs[str(p)]={'sha256':R.sha(p),'bytes':p.stat().st_size}
            paths={}
            for layer in layers:
                state=source/ds/f'chat_L{layer}.npy';x=np.load(state,mmap_mode='r',allow_pickle=False)
                if x.shape!=(len(ids),5120):raise ValueError(f'State shape mismatch: {state}')
                inputs[str(state)]={'sha256':R.sha(state),'bytes':state.stat().st_size};paths[str(layer)]=str(state)
            cache[ds]=(idx,{v:i for i,v in enumerate(ids)},paths)
        idx,pos,paths=cache[ds]
        if item['item_id'] not in pos:raise ValueError(f'Missing state item: {item["item_id"]}')
        row=pos[item['item_id']]
        if idx.get('splits') and idx['splits'][row]!=item['split']:raise ValueError(f'State split mismatch: {item["item_id"]}')
        if idx.get('labels') and int(idx['labels'][row])!=int(item['label']):raise ValueError(f'State label mismatch: {item["item_id"]}')
        bound.append(dict(item,state_row=row,state_paths=paths))
    return bound,inputs


def join_rebuilt(items,union):
    union=Path(union);m=read(union/'union_manifest.json')
    name='reconstructions.jsonl'
    if R.sha(union/name)!=m['output_sha256'][name]:raise ValueError('Rebuilt source hash mismatch')
    wanted={r['item_id'] for r in items if r['population']=='main' and r['split']=='test'}
    lookup={}
    for r in lines(union/name):
        sid=r.get('state_item_id');rid=r.get('reconstruction_id')
        if sid in wanted and rid=='state|'+sid:
            if sid in lookup:raise ValueError(f'Duplicate reconstruction: {sid}')
            if not r.get('text','').strip():raise ValueError(f'Empty reconstruction: {sid}')
            lookup[sid]=r
    if wanted-set(lookup):raise ValueError(f'Missing reconstructed IDs: {sorted(wanted-set(lookup))}')
    return lookup
