"""§196 Arm A only. Does not evaluate, reopen or replace Arm B behaviour."""
import argparse
from pathlib import Path
from .core import *

ROWS={'nesting_depth','indent_level','page_range_digit'}
DOSES=(.25,.5,1,2,4)

def collect(s):
    for p,h in s['inputs'].items():
        require(sha(p)==h,'frozen CPU input changed')
    key=unique(read(s['key']))
    plan=read(s['judge_plan'])['judge_values']
    root=Path(s['output']); z=verify(root/'OUTPUT_SEAL.json',s['output_sha256'])
    require(z['status']=='COMPLETE' and z['experiment']=='E79','complete E79 output')
    require(z['input_seal_sha256']==s['input_sha256'],'executed input identity')
    grid=read(root/'JOB_GRID.json')
    require(read(root/'COMPLETED.json')==list(range(len(grid))),'all jobs completed')
    items=read(s['items']); rows=[]
    for number,job in enumerate(grid):
        if job['kind']!='native':
            continue
        payload=read(root/'jobs'/f'{number:06d}.json')
        require(len(payload)==len(job['indices']),'native batch cardinality')
        for x,index in zip(payload,job['indices']):
            require(x['id']==items[index]['id'],'source item identity')
            k=key[x['id']]
            if k['arm']!='A':
                continue
            require(k['target_label'] in (0,1),'private binary target')
            v=plan[k['source_item_id']]
            rows.append(dict(id=x['id'],item=k['source_item_id'],row=k['row'],reader='oracle',
                 direction=k['condition'],alpha=k['alpha'],target='A' if k['target_label']==1 else 'B',
                 property=k['row'],values=dict(A=v[0],B=v[1]),text=x['text']))
    validate_grid(rows)
    return rows

def validate_grid(rows):
    require(len(rows)==4032 and {x['row'] for x in rows}==ROWS,'Arm A exact 3x16x84 grid')
    unique(rows)
    cells={'none'}|{f'{d}:{a}' for d in ('J','nonJ','random') for a in DOSES}
    for row in ROWS:
        groups={}
        for x in rows:
            if x['row']!=row: continue
            c='none' if x['alpha'] in (0,None) else f"{x['direction']}:{x['alpha']}"
            groups.setdefault(c,[]).append(x)
        require(set(groups)==cells,'dose/direction grid')
        reference=None; targets={}
        for xs in groups.values():
            ids={x['item'] for x in xs}
            require(len(xs)==len(ids)==84,'84 unique items/cell')
            require(sum(x['target']=='A' for x in xs)==42,'balanced injected targets')
            if reference is None: reference=ids
            require(reference==ids,'paired items across cells')
            for x in xs:
                require(targets.setdefault(x['item'],x['target'])==x['target'],'target changes across dose')

def analyze(rows):
    cells={}
    for x in rows:
        c='none' if x['alpha'] in (0,None) else f"{x['direction']}:{x['alpha']}"
        cells.setdefault(x['row'],{}).setdefault(c,{})[x['item']]=x['score']
    result={}; passes=0
    for row in sorted(ROWS):
        c=cells[row]; rates={k:stats(v) for k,v in c.items()}; contrasts={}; passing=[]
        for a in DOSES:
            d=stats(c[f'J:{a}'],c[f'nonJ:{a}']); j=rates[f'J:{a}']['estimate']
            ok=None if j is None or d['CI95'] is None else round(j,12)>=.30 and round(d['estimate'],12)>=.30 and d['CI95'][0]>0
            contrasts[str(a)]=dict(d,passes=ok,rule_eligible=a<=2)
            if ok and a<=2: passing.append(a)
        status='MET' if passing else 'NOT EVALUABLE' if any(contrasts[str(a)]['passes'] is None for a in DOSES if a<=2) else 'NOT MET'
        passes+=bool(passing)
        traj=[rates['none']['estimate']]+[rates[f'J:{a}']['estimate'] for a in DOSES if a<=2]
        result[row]=dict(rates=rates,contrasts=contrasts,passing_doses=passing,status=status,
                        monotone_0_to_2=None if None in traj else all(round(y-x,12)>=0 for x,y in zip(traj,traj[1:])))
    deltas=[r['contrasts'][str(a)]['estimate'] for r in result.values() for a in DOSES if a<=2]
    return dict(R_C1='MET' if passes>=2 else 'NOT EVALUABLE' if any(r['status']=='NOT EVALUABLE' for r in result.values()) else 'NOT MET',
                states=result,passing_states=passes,measure='S_target',alpha4='DESCRIPTIVE ONLY',
                falsifier=False if any(d is not None and round(d,12)>=.10 for d in deltas) else None if None in deltas else True,
                R_C2='NOT IN THIS ARM A ADAPTER')

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['blind','analyze']);a=p.parse_args()
    commit=committed();s=read(HERE/'E79.json')
    if a.mode=='blind':
        export(collect(s),s['blind'],s['private'],s['output_sha256'],commit)
    else:
        rows,jsha=load_codes(s);validate_grid(rows)
        # Required pre-existing diagnostics are copied verbatim, never tuned or used as post-hoc exclusions.
        require(sha(s['diagnostics'])==s['diagnostics_sha256'],'pinned diagnostics')
        verify(Path(s['manipulation'])/'MANIPULATION_SEAL.json',s['manipulation_seal_sha256'])
        out=claim(s,commit)
        result=analyze(rows)
        write(out/'RESULTS.json',result)
        # Retain original item grid and masks when excluding privacy-redacted readouts.
        sensitivity=[dict(x,score=None if x['redacted'] else x['score']) for x in rows]
        write(out/'REDACTION_SENSITIVITY.json',analyze(sensitivity))
        write(out/'DIAGNOSTICS.json',read(s['diagnostics']))
        write(out/'MANIPULATION.json',read(Path(s['manipulation'])/'MANIPULATION.json'))
        write(out/'SCORED_ITEMS.json',rows)
        seal(out,'ANALYSIS_SEAL.json',experiment='E79_ARM_A',status='COMPLETE_ONCE',
             output_seal_sha256=s['output_sha256'],judgment_seal_sha256=jsha,code_commit=commit)

if __name__=='__main__': main()
