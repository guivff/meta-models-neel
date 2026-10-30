"""Once-only completion of the §146 descriptive impact audit; no verdict reruns."""
import argparse,json,shutil
from pathlib import Path
from collections import Counter
from projects.g_agreement.blindspot import protocol as P
from .e24_worker import seal
CONDITION={'prose_sentence','latex_item'}


def population(entries):
    items={}
    for e in entries:
        if e.get('format')=='indexed':
            ids=json.loads(Path(e['ids']).read_text());groups=json.loads(Path(e['path']).read_text())
            rows=[{'id':ids[i],'row':f} for f,g in groups.items() for i in g['indices']]
        else:rows=P.rows(Path(e['path']))
        for r in rows:
            uid=r.get('id',r.get('item_id'));row=e.get('row',r.get('row',r.get('feature')))
            if not uid or not row:raise ValueError('missing item/row metadata')
            if uid in items and items[uid]!=row:raise ValueError('conflicting row metadata')
            items[uid]=row
    if not items:raise ValueError('empty sealed population')
    affected=sum(r in CONDITION for r in items.values())
    return {'items':len(items),'condition_items':affected,'fraction':affected/len(items),'rows':dict(Counter(items.values()))}


def analyse(spec):
    original=Path(spec['prior_audit']);P.verify(original,'AUDIT_SEAL.json')
    summary=json.loads((original/'SUMMARY.json').read_text());mismatches=P.rows(original/'MISMATCHES.jsonl')
    if len(mismatches)!=18 or summary['C_D_agree']!=482:raise ValueError('prior audit identity')
    if {r['row'] for r in mismatches}!=CONDITION:raise ValueError('row envelope changed')
    selected=json.loads(Path(spec['selected']).read_text())
    n=sum(x['row'] in CONDITION for x in selected)
    condition={'predicate':"row in {'prose_sentence', 'latex_item'}",'status':'DESCRIPTIVE_ROW_ENVELOPE_NOT_CAUSAL_OR_PERFECT_SEPARATOR',
       'all_mismatches_covered':True,'condition_items_among_500':n,'mismatches_in_condition':18,'passing_items_in_condition':n-18,
       'padding_positive_not_necessary':any(x['W1_batch_padding']==0 for x in mismatches),
       'length_range_of_failures':[min(x['length'] for x in mismatches),max(x['length'] for x in mismatches)],
       'interpretation':'Rows localize all observed failures but also contain passing items. No causal padding or length rule is certified. Exposure fractions below use this conservative row envelope, not a failure-rate estimate.'}
    inventory=[]
    for run in spec['runs']:
        result={k:run[k] for k in ('experiment','owner','status')}
        if run['status']=='SEALED':
            result.update(population(run['populations']))
            result['sensitivity_required']=result['condition_items']>0 and summary['sensitivity_triggered']
            result['owner_review']='PENDING; no sealed verdict altered'
        else:result.update(items=None,condition_items=None,fraction=None,owner_review='WAIT_FOR_SEALED_RUN')
        inventory.append(result)
    out=Path(spec['out']);out.mkdir(parents=True,exist_ok=False)
    for name in ('MISMATCHES.jsonl','SUMMARY.json'):shutil.copyfile(original/name,out/name)
    P.dump(out/'CONDITION.json',condition);P.dump(out/'RUN_FRACTIONS.json',inventory)
    lines=[(original/'RESULTS.md').read_text(),'\n## Condition and run coverage\n',condition['interpretation'],f'\n18/{n} items in the row envelope fail; {n-18} pass. A failed item has zero W1 padding, so positive padding is not necessary.\n',
           '| Run | Owner | Condition items / unique scored items | Fraction | Status |','|---|---|---:|---:|---|']
    for r in inventory:
        fraction='NA' if r['fraction'] is None else f"{r['fraction']:.6f}"
        lines.append(f"| {r['experiment']} | {r['owner']} | {r['condition_items']} / {r['items']} | {fraction} | {r['status']} |")
    lines+=['','Counts deduplicate item IDs across readers, arms, doses and checkpoints. Zero row-envelope exposure is not proof of capture invariance. No registered analysis or original verdict is rerun. The previously computed cosine audit is adopted with its original seal; this command only completes the descriptive inventory.','',
            '13/18 cos(W1,C) values are below 0.99: owner sensitivity comparisons remain required for exposed runs. This command reports exposure and does not claim those comparisons or owner reviews are complete. E36 has no complete output seal at packet preparation and remains pending.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    seal(out,['MISMATCHES.jsonl','SUMMARY.json','CONDITION.json','RUN_FRACTIONS.json','RESULTS.md'],'AUDIT_SEAL.json','SECTION149_IMPACT_INVENTORY_OWNER_REVIEW_PENDING')


def run(path,expected):
    if P.sha(path)!=expected:raise ValueError('spec hash')
    spec=json.loads(path.read_text());lock=Path(spec['lock']);lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as f:json.dump({'spec_sha256':expected,'label':'§149 RUN-BY-INTEGRATOR'},f)
    try:
        if Path(spec['out']).exists():raise ValueError('output exists')
        for n,h in spec['pins'].items():
            if P.sha(n)!=h:raise ValueError('input/code pin changed: '+n)
        for entry in spec['seals']:P.verify(Path(entry['directory']),entry['name'])
        analyse(spec)
        P.dump(lock.with_suffix('.receipt.json'),{'status':'COMPLETE','retry_authorized':False,'label':'§149 RUN-BY-INTEGRATOR'})
    except BaseException as exc:
        P.dump(lock.with_suffix('.receipt.json'),{'status':'STOP_OWNER_REQUIRED','error':str(exc),'retry_authorized':False});raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--spec-sha256',required=True);a=p.parse_args();run(a.spec,a.spec_sha256)
